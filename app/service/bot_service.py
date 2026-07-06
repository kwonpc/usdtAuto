import asyncio
import logging
from datetime import datetime, time, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import Database, utc_now
from app.db_models import BotSetting, PriceSnapshot, Trade, TradingBot, UpbitApiKey
from app.exchange.factory import create_exchange_client
from app.fx.api_provider import ApiFxRateProvider
from app.models import BotStatus, Signal, StrategyType
from app.schemas import BotSettingsRequest
from app.service.paper_trade_service import PaperTradeService
from app.strategy.base import StrategyContext
from app.strategy.base_price_gap_strategy import BasePriceGapStrategy
from app.strategy.premium_rebalance_strategy import PremiumRebalanceStrategy


logger = logging.getLogger(__name__)


class TemporaryTickError(Exception):
    pass


class BotManager:
    def __init__(self, settings: Settings, database: Database):
        self.settings = settings
        self.database = database
        self.exchange_clients = {
            "upbit": create_exchange_client("upbit", settings),
            "bithumb": create_exchange_client("bithumb", settings),
        }
        self.fx_api_provider = ApiFxRateProvider()
        self._lock = asyncio.Lock()

    def ensure_default_bot(self, db: Session, user_id: int) -> TradingBot:
        bot = db.scalar(select(TradingBot).where(TradingBot.user_id == user_id).order_by(TradingBot.id.asc()))
        if bot is not None:
            return bot

        bot = TradingBot(user_id=user_id, name="Default KRW-USDT Bot", exchange=self.settings.exchange, market=self.settings.market)
        db.add(bot)
        db.flush()
        setting = BotSetting(
            bot_id=bot.id,
            initial_balance=self.settings.initial_balance,
            buy_premium_threshold=self.settings.buy_premium_threshold,
            sell_premium_threshold=self.settings.sell_premium_threshold,
            neutral_band=self.settings.neutral_band,
            round_trip_fee_rate=self.settings.round_trip_fee_rate,
            max_order_amount=self.settings.max_order_amount,
            daily_max_trade_amount=self.settings.daily_max_trade_amount,
            daily_max_loss_rate=self.settings.daily_max_loss_rate,
            fx_provider=self.settings.fx_provider,
            manual_usd_krw_rate=self.settings.manual_usd_krw_rate,
            fx_rate_max_stale_seconds=self.settings.fx_rate_max_stale_seconds,
        )
        db.add(setting)
        db.flush()
        return bot

    def get_user_bot(self, db: Session, user_id: int, bot_id: int | None = None) -> TradingBot:
        if bot_id is None:
            return self.ensure_default_bot(db, user_id)
        bot = db.scalar(select(TradingBot).where(TradingBot.id == bot_id, TradingBot.user_id == user_id))
        if bot is None:
            raise ValueError("Bot not found")
        return bot

    def update_settings(self, db: Session, user_id: int, payload: BotSettingsRequest, bot_id: int | None = None) -> TradingBot:
        bot = self.get_user_bot(db, user_id, bot_id)
        if payload.api_key_id is not None:
            api_key = db.scalar(
                select(UpbitApiKey).where(
                    UpbitApiKey.id == payload.api_key_id,
                    UpbitApiKey.user_id == user_id,
                    UpbitApiKey.exchange == payload.exchange,
                )
            )
            if api_key is None:
                raise ValueError("API key not found")

        bot.exchange = payload.exchange
        bot.market = payload.market
        bot.trade_mode = payload.trade_mode
        bot.strategy_type = payload.strategy_type
        bot.api_key_id = payload.api_key_id
        setting = bot.settings
        setting.buy_premium_threshold = payload.buy_premium_threshold
        setting.sell_premium_threshold = payload.sell_premium_threshold
        setting.neutral_band = payload.neutral_band
        setting.base_price = payload.base_price
        setting.price_gap = payload.price_gap
        setting.round_trip_fee_rate = payload.round_trip_fee_rate
        setting.max_order_amount = payload.max_order_amount
        setting.daily_max_trade_amount = payload.daily_max_trade_amount
        setting.daily_max_loss_rate = payload.daily_max_loss_rate
        setting.fx_provider = payload.fx_provider
        setting.manual_usd_krw_rate = payload.manual_usd_krw_rate
        setting.fx_rate_max_stale_seconds = payload.fx_rate_max_stale_seconds
        db.flush()
        return bot

    def start(self, db: Session, user_id: int, bot_id: int | None = None) -> TradingBot:
        bot = self.get_user_bot(db, user_id, bot_id)
        if bot.trade_mode == "live":
            bot.bot_status = BotStatus.ERROR.value
            bot.last_error = "실거래 주문 실행은 아직 구현되지 않았습니다. 가상매매 모드를 사용하세요."
        else:
            bot.bot_status = BotStatus.RUNNING.value
            bot.last_error = None
        db.flush()
        return bot

    def stop(self, db: Session, user_id: int, bot_id: int | None = None) -> TradingBot:
        bot = self.get_user_bot(db, user_id, bot_id)
        bot.bot_status = BotStatus.STOPPED.value
        db.flush()
        return bot

    def manual_sell(self, db: Session, user_id: int, price: float, volume: float | None = None, bot_id: int | None = None) -> Trade:
        bot = self.get_user_bot(db, user_id, bot_id)
        if bot.trade_mode == "live":
            raise ValueError("Live manual sell is not implemented yet. Use paper mode.")
        paper_trader = PaperTradeService(db, user_id, bot.id, bot.settings, bot.exchange)
        trade = paper_trader.manual_sell(price=price, trade_mode=bot.trade_mode, volume=volume)
        if trade is None:
            raise ValueError("No USDT balance to sell")
        bot.last_signal = Signal.SELL.value
        bot.last_signal_at = trade.created_at
        bot.last_error = None
        db.flush()
        return trade

    async def tick_all(self) -> None:
        async with self._lock:
            with self.database.session() as db:
                bots = db.scalars(select(TradingBot).where(TradingBot.bot_status == BotStatus.RUNNING.value)).all()
                for bot in bots:
                    await self._tick(db, bot)

    async def _tick(self, db: Session, bot: TradingBot) -> None:
        try:
            await self._run_tick(db, bot)
        except TemporaryTickError as exc:
            bot.last_error = str(exc)
            logger.warning("Temporary tick failure for bot %s: %s", bot.id, exc)
            db.flush()
        except Exception as exc:
            bot.bot_status = BotStatus.ERROR.value
            bot.last_error = str(exc)
            logger.exception("Fatal tick failure for bot %s", bot.id)
            db.flush()

    async def _run_tick(self, db: Session, bot: TradingBot) -> None:
        setting = bot.settings
        paper_trader = PaperTradeService(db, bot.user_id, bot.id, setting, bot.exchange)
        try:
            exchange_client = self.exchange_clients.get(bot.exchange)
            if exchange_client is None:
                raise RuntimeError(f"Unsupported exchange: {bot.exchange}")
            ticker = await exchange_client.get_ticker(bot.market)
            usd_krw_rate = await self._get_usd_krw_rate(setting)
        except Exception as exc:
            raise TemporaryTickError(f"일시적 시세/환율 조회 실패: {exc}") from exc

        decision = self._decide(bot, setting, paper_trader, ticker.trade_price, usd_krw_rate)

        db.add(
            PriceSnapshot(
                user_id=bot.user_id,
                bot_id=bot.id,
                exchange=bot.exchange,
                market=ticker.market,
                trade_price=ticker.trade_price,
                bid_price=ticker.bid_price,
                ask_price=ticker.ask_price,
                usd_krw_rate=usd_krw_rate,
                premium_rate=decision.premium_rate,
            )
        )

        signal = self._apply_risk_controls(db, bot, setting, paper_trader, decision.signal, ticker.trade_price)
        if signal in (Signal.BUY, Signal.SELL):
            remaining_trade_amount = setting.daily_max_trade_amount - self.today_trade_amount(db, bot.user_id, bot.id)
            trade = paper_trader.execute(
                signal,
                ticker.ask_price if signal == Signal.BUY else ticker.bid_price,
                trade_mode=bot.trade_mode,
                max_order_amount=remaining_trade_amount,
            )
            if trade is not None:
                bot.last_signal = signal.value
                bot.last_signal_at = trade.created_at
        else:
            bot.last_signal = decision.signal.value
            bot.last_signal_at = utc_now()

        bot.last_error = None
        db.flush()

    async def _get_usd_krw_rate(self, setting: BotSetting) -> float | None:
        if setting.fx_provider == "api":
            fx_rate = await self.fx_api_provider.get_usd_krw_rate()
            age_seconds = (datetime.now(timezone.utc) - fx_rate.fetched_at).total_seconds()
            if age_seconds > setting.fx_rate_max_stale_seconds:
                raise RuntimeError("FX rate is stale")
            return fx_rate.rate
        return setting.manual_usd_krw_rate

    def _decide(
        self,
        bot: TradingBot,
        setting: BotSetting,
        paper_trader: PaperTradeService,
        trade_price: float,
        usd_krw_rate: float | None,
    ):
        context = StrategyContext(
            trade_price=trade_price,
            usd_krw_rate=usd_krw_rate,
            avg_buy_price=paper_trader.portfolio.avg_buy_price,
            usdt_balance=paper_trader.portfolio.usdt_balance,
        )
        if bot.strategy_type == StrategyType.BASE_PRICE_GAP.value:
            return BasePriceGapStrategy(setting.base_price, setting.price_gap).decide(context)
        return PremiumRebalanceStrategy(setting.buy_premium_threshold, setting.sell_premium_threshold).decide(context)

    def _apply_risk_controls(
        self,
        db: Session,
        bot: TradingBot,
        setting: BotSetting,
        paper_trader: PaperTradeService,
        signal: Signal,
        mark_price: float,
    ) -> Signal:
        if signal == Signal.HOLD:
            return signal

        daily_amount = self.today_trade_amount(db, bot.user_id, bot.id)
        if daily_amount >= setting.daily_max_trade_amount:
            bot.bot_status = BotStatus.PAUSED_BY_RISK.value
            return Signal.HOLD

        total_asset = paper_trader.total_asset_krw(mark_price)
        loss_rate = ((total_asset / setting.initial_balance) - 1) * 100
        if loss_rate <= setting.daily_max_loss_rate:
            bot.bot_status = BotStatus.PAUSED_BY_RISK.value
            return Signal.HOLD

        return signal

    def latest_snapshot(self, db: Session, user_id: int, bot_id: int) -> PriceSnapshot | None:
        return db.scalar(
            select(PriceSnapshot)
            .where(PriceSnapshot.user_id == user_id, PriceSnapshot.bot_id == bot_id)
            .order_by(PriceSnapshot.id.desc())
        )

    def recent_trades(self, db: Session, user_id: int, bot_id: int, limit: int = 50) -> list[Trade]:
        return list(
            db.scalars(
                select(Trade)
                .where(Trade.user_id == user_id, Trade.bot_id == bot_id)
                .order_by(Trade.id.desc())
                .limit(limit)
            )
        )

    def today_trade_count(self, db: Session, user_id: int, bot_id: int) -> int:
        start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
        return int(
            db.scalar(
                select(func.count(Trade.id)).where(
                    Trade.user_id == user_id,
                    Trade.bot_id == bot_id,
                    Trade.created_at >= start,
                )
            )
            or 0
        )

    def today_trade_amount(self, db: Session, user_id: int, bot_id: int) -> float:
        start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
        return float(
            db.scalar(
                select(func.coalesce(func.sum(Trade.price * Trade.volume), 0)).where(
                    Trade.user_id == user_id,
                    Trade.bot_id == bot_id,
                    Trade.created_at >= start,
                )
            )
            or 0
        )

    def today_profit(self, db: Session, user_id: int, bot_id: int) -> float:
        start = datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)
        return float(
            db.scalar(
                select(func.coalesce(func.sum(Trade.profit), 0)).where(
                    Trade.user_id == user_id,
                    Trade.bot_id == bot_id,
                    Trade.created_at >= start,
                )
            )
            or 0
        )

    def status_payload(self, db: Session, user_id: int, bot_id: int | None = None) -> dict[str, Any]:
        bot = self.get_user_bot(db, user_id, bot_id)
        snapshot = self.latest_snapshot(db, user_id, bot.id)
        mark_price = float(snapshot.trade_price) if snapshot else 0.0
        paper_trader = PaperTradeService(db, user_id, bot.id, bot.settings, bot.exchange)
        portfolio = paper_trader.portfolio
        return {
            "botId": bot.id,
            "botName": bot.name,
            "botStatus": bot.bot_status,
            "exchange": bot.exchange,
            "tradeMode": bot.trade_mode,
            "strategyType": bot.strategy_type,
            "exchangeUsdtPrice": mark_price,
            "upbitUsdtPrice": mark_price,
            "usdKrwRate": float(snapshot.usd_krw_rate) if snapshot and snapshot.usd_krw_rate is not None else None,
            "premiumRate": float(snapshot.premium_rate) if snapshot and snapshot.premium_rate is not None else None,
            "krwBalance": portfolio.krw_balance,
            "usdtBalance": portfolio.usdt_balance,
            "avgBuyPrice": portfolio.avg_buy_price,
            "totalAssetKrw": paper_trader.total_asset_krw(mark_price),
            "todayTradeCount": self.today_trade_count(db, user_id, bot.id),
            "todayProfit": self.today_profit(db, user_id, bot.id),
            "lastSignal": bot.last_signal,
            "lastSignalAt": bot.last_signal_at.isoformat() if bot.last_signal_at else None,
            "lastError": bot.last_error,
        }
