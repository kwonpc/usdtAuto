from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db_models import BotSetting, Trade
from app.models import Signal, TradeStatus


@dataclass
class PaperPortfolio:
    krw_balance: float
    usdt_balance: float
    avg_buy_price: float = 0.0
    realized_profit: float = 0.0


class PaperTradeService:
    def __init__(self, db: Session, user_id: int, bot_id: int, setting: BotSetting, exchange: str = "upbit"):
        self.db = db
        self.user_id = user_id
        self.bot_id = bot_id
        self.setting = setting
        self.exchange = exchange
        self.portfolio = self._restore_from_trades()

    def _restore_from_trades(self) -> PaperPortfolio:
        rows = self.db.scalars(
            select(Trade).where(Trade.user_id == self.user_id, Trade.bot_id == self.bot_id).order_by(Trade.id.asc())
        ).all()

        portfolio = PaperPortfolio(krw_balance=self.setting.initial_balance, usdt_balance=0.0)
        for row in rows:
            if row.side == Signal.BUY.value:
                cost = row.price * row.volume
                previous_value = portfolio.avg_buy_price * portfolio.usdt_balance
                portfolio.krw_balance -= cost + row.fee
                portfolio.usdt_balance += row.volume
                portfolio.avg_buy_price = (previous_value + cost) / portfolio.usdt_balance
            elif row.side == Signal.SELL.value:
                proceeds = row.price * row.volume
                portfolio.krw_balance += proceeds - row.fee
                portfolio.usdt_balance -= row.volume
                portfolio.realized_profit += row.profit
                if portfolio.usdt_balance <= 1e-12:
                    portfolio.usdt_balance = 0.0
                    portfolio.avg_buy_price = 0.0
        return portfolio

    @property
    def fee_rate_per_side(self) -> float:
        return self.setting.round_trip_fee_rate / 2

    def total_asset_krw(self, mark_price: float) -> float:
        return self.portfolio.krw_balance + (self.portfolio.usdt_balance * mark_price)

    def execute(self, signal: Signal, price: float, trade_mode: str, max_order_amount: float | None = None) -> Trade | None:
        if signal == Signal.BUY:
            return self._buy(price, trade_mode, max_order_amount)
        if signal == Signal.SELL:
            return self._sell(price, trade_mode, max_order_amount)
        return None

    def manual_sell(self, price: float, trade_mode: str, volume: float | None = None) -> Trade | None:
        if self.portfolio.usdt_balance <= 0:
            return None
        target_volume = self.portfolio.usdt_balance if volume is None else min(volume, self.portfolio.usdt_balance)
        if target_volume <= 0:
            return None
        return self._sell_volume(price, target_volume, trade_mode)

    def _buy(self, price: float, trade_mode: str, max_order_amount: float | None) -> Trade | None:
        order_limit = self.setting.max_order_amount if max_order_amount is None else max_order_amount
        order_amount = min(order_limit, self.portfolio.krw_balance)
        if order_amount <= 0:
            return None

        fee = order_amount * self.fee_rate_per_side
        spendable = order_amount - fee
        if spendable <= 0:
            return None

        volume = spendable / price
        previous_value = self.portfolio.avg_buy_price * self.portfolio.usdt_balance
        self.portfolio.krw_balance -= order_amount
        self.portfolio.usdt_balance += volume
        self.portfolio.avg_buy_price = (previous_value + spendable) / self.portfolio.usdt_balance
        return self._insert_trade(Signal.BUY, price, volume, fee, 0.0, 0.0, self.total_asset_krw(price), trade_mode)

    def _sell(self, price: float, trade_mode: str, max_order_amount: float | None) -> Trade | None:
        if self.portfolio.usdt_balance <= 0:
            return None

        order_limit = self.setting.max_order_amount if max_order_amount is None else max_order_amount
        max_volume_by_amount = order_limit / price
        volume = min(self.portfolio.usdt_balance, max_volume_by_amount)
        return self._sell_volume(price, volume, trade_mode)

    def _sell_volume(self, price: float, volume: float, trade_mode: str) -> Trade | None:
        if volume <= 0:
            return None
        gross = price * volume
        fee = gross * self.fee_rate_per_side
        proceeds = gross - fee
        cost_basis = self.portfolio.avg_buy_price * volume
        profit = proceeds - cost_basis
        profit_rate = (profit / cost_basis * 100) if cost_basis else 0.0

        self.portfolio.krw_balance += proceeds
        self.portfolio.usdt_balance -= volume
        self.portfolio.realized_profit += profit
        if self.portfolio.usdt_balance <= 1e-12:
            self.portfolio.usdt_balance = 0.0
            self.portfolio.avg_buy_price = 0.0

        return self._insert_trade(Signal.SELL, price, volume, fee, profit, profit_rate, self.total_asset_krw(price), trade_mode)

    def _insert_trade(
        self,
        side: Signal,
        price: float,
        volume: float,
        fee: float,
        profit: float,
        profit_rate: float,
        total_asset_krw: float,
        trade_mode: str,
    ) -> Trade:
        trade = Trade(
            user_id=self.user_id,
            bot_id=self.bot_id,
            exchange=self.exchange,
            side=side.value,
            price=price,
            volume=volume,
            fee=fee,
            profit=profit,
            profit_rate=profit_rate,
            total_asset_krw=total_asset_krw,
            trade_mode=trade_mode,
            status=TradeStatus.FILLED.value,
        )
        self.db.add(trade)
        self.db.flush()
        return trade
