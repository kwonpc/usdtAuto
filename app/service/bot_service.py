import asyncio
from datetime import datetime, timezone
from typing import Any

from app.config import Settings
from app.database import Database, utc_now_iso
from app.exchange.upbit import UpbitClient
from app.fx.api_provider import ApiFxRateProvider
from app.fx.manual_provider import ManualFxRateProvider
from app.fx.provider import FxRateProvider
from app.models import BotStatus, Signal
from app.service.paper_trade_service import PaperTradeService
from app.strategy.premium_rebalance_strategy import PremiumRebalanceStrategy


class BotService:
    def __init__(self, settings: Settings, database: Database):
        self.settings = settings
        self.database = database
        self.status = BotStatus.STOPPED
        self.last_signal = Signal.HOLD
        self.last_signal_at: str | None = None
        self.last_error: str | None = None
        self.upbit = UpbitClient(settings)
        self.fx_provider = self._create_fx_provider()
        self.strategy = PremiumRebalanceStrategy(settings)
        self.paper_trader = PaperTradeService(settings, database)
        self._lock = asyncio.Lock()

    def _create_fx_provider(self) -> FxRateProvider:
        if self.settings.fx_provider == "api":
            return ApiFxRateProvider()
        return ManualFxRateProvider(self.settings)

    def start(self) -> None:
        if self.settings.trade_mode == "live":
            self.status = BotStatus.ERROR
            self.last_error = "Live trading is not implemented in MVP. Set trade_mode to paper."
            return
        if self.status != BotStatus.ERROR:
            self.status = BotStatus.RUNNING

    def stop(self) -> None:
        self.status = BotStatus.STOPPED

    async def tick(self) -> None:
        if self.status != BotStatus.RUNNING:
            return

        async with self._lock:
            try:
                ticker = await self.upbit.get_ticker()
                fx_rate = await self.fx_provider.get_usd_krw_rate()
                self._validate_fx_rate(fx_rate.fetched_at)
                decision = self.strategy.decide(ticker.trade_price, fx_rate.rate)
                self._insert_price_snapshot(
                    ticker.market,
                    ticker.trade_price,
                    ticker.bid_price,
                    ticker.ask_price,
                    fx_rate.rate,
                    decision.premium_rate,
                )

                signal = self._apply_risk_controls(decision.signal, ticker.trade_price)
                if signal in (Signal.BUY, Signal.SELL):
                    remaining_trade_amount = self.settings.daily_max_trade_amount - self.today_trade_amount()
                    trade = self.paper_trader.execute(
                        signal,
                        ticker.ask_price if signal == Signal.BUY else ticker.bid_price,
                        max_order_amount=remaining_trade_amount,
                    )
                    if trade is not None:
                        self.last_signal = signal
                        self.last_signal_at = trade["created_at"]
                else:
                    self.last_signal = decision.signal
                    self.last_signal_at = utc_now_iso()

                self.last_error = None
            except Exception as exc:
                self.status = BotStatus.ERROR
                self.last_error = str(exc)

    def _validate_fx_rate(self, fetched_at: datetime) -> None:
        age_seconds = (datetime.now(timezone.utc) - fetched_at).total_seconds()
        if age_seconds > self.settings.fx_rate_max_stale_seconds:
            self.status = BotStatus.PAUSED_BY_RISK
            raise RuntimeError("FX rate is stale")

    def _apply_risk_controls(self, signal: Signal, mark_price: float) -> Signal:
        if signal == Signal.HOLD:
            return signal

        daily_amount = self.today_trade_amount()
        if daily_amount >= self.settings.daily_max_trade_amount:
            self.status = BotStatus.PAUSED_BY_RISK
            return Signal.HOLD

        total_asset = self.paper_trader.total_asset_krw(mark_price)
        loss_rate = ((total_asset / self.settings.initial_balance) - 1) * 100
        if loss_rate <= self.settings.daily_max_loss_rate:
            self.status = BotStatus.PAUSED_BY_RISK
            return Signal.HOLD

        return signal

    def _insert_price_snapshot(
        self,
        market: str,
        trade_price: float,
        bid_price: float,
        ask_price: float,
        usd_krw_rate: float,
        premium_rate: float,
    ) -> None:
        with self.database.connect() as conn:
            conn.execute(
                """
                INSERT INTO price_snapshot
                    (market, trade_price, bid_price, ask_price, usd_krw_rate, premium_rate, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (market, trade_price, bid_price, ask_price, usd_krw_rate, premium_rate, utc_now_iso()),
            )

    def latest_snapshot(self) -> dict[str, Any] | None:
        with self.database.connect() as conn:
            row = conn.execute("SELECT * FROM price_snapshot ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None

    def recent_trades(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.database.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM virtual_trade ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def today_trade_count(self) -> int:
        with self.database.connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM virtual_trade WHERE date(created_at) = date('now')"
            ).fetchone()
        return int(row["count"])

    def today_trade_amount(self) -> float:
        with self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(price * volume), 0) AS amount
                FROM virtual_trade
                WHERE date(created_at) = date('now')
                """
            ).fetchone()
        return float(row["amount"])

    def today_profit(self) -> float:
        with self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(profit), 0) AS profit
                FROM virtual_trade
                WHERE date(created_at) = date('now')
                """
            ).fetchone()
        return float(row["profit"])

    def status_payload(self) -> dict[str, Any]:
        snapshot = self.latest_snapshot()
        mark_price = float(snapshot["trade_price"]) if snapshot else 0.0
        portfolio = self.paper_trader.portfolio
        return {
            "botStatus": self.status.value,
            "tradeMode": self.settings.trade_mode,
            "upbitUsdtPrice": mark_price,
            "usdKrwRate": float(snapshot["usd_krw_rate"]) if snapshot else None,
            "premiumRate": float(snapshot["premium_rate"]) if snapshot else None,
            "krwBalance": portfolio.krw_balance,
            "usdtBalance": portfolio.usdt_balance,
            "avgBuyPrice": portfolio.avg_buy_price,
            "totalAssetKrw": self.paper_trader.total_asset_krw(mark_price),
            "todayTradeCount": self.today_trade_count(),
            "todayProfit": self.today_profit(),
            "lastSignal": self.last_signal.value,
            "lastSignalAt": self.last_signal_at,
            "lastError": self.last_error,
        }
