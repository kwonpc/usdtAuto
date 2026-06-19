from dataclasses import dataclass

from app.config import Settings
from app.database import Database, utc_now_iso
from app.models import Signal


@dataclass
class PaperPortfolio:
    krw_balance: float
    usdt_balance: float
    avg_buy_price: float = 0.0
    realized_profit: float = 0.0


class PaperTradeService:
    def __init__(self, settings: Settings, database: Database):
        self.settings = settings
        self.database = database
        self.portfolio = PaperPortfolio(krw_balance=settings.initial_balance, usdt_balance=0.0)
        self._restore_from_trades()

    def _restore_from_trades(self) -> None:
        with self.database.connect() as conn:
            rows = conn.execute("SELECT * FROM virtual_trade ORDER BY id ASC").fetchall()

        portfolio = PaperPortfolio(krw_balance=self.settings.initial_balance, usdt_balance=0.0)
        for row in rows:
            side = row["side"]
            price = float(row["price"])
            volume = float(row["volume"])
            fee = float(row["fee"])
            if side == Signal.BUY.value:
                cost = price * volume
                previous_value = portfolio.avg_buy_price * portfolio.usdt_balance
                portfolio.krw_balance -= cost + fee
                portfolio.usdt_balance += volume
                portfolio.avg_buy_price = (previous_value + cost) / portfolio.usdt_balance
            elif side == Signal.SELL.value:
                proceeds = price * volume
                portfolio.krw_balance += proceeds - fee
                portfolio.usdt_balance -= volume
                portfolio.realized_profit += float(row["profit"])
                if portfolio.usdt_balance <= 1e-12:
                    portfolio.usdt_balance = 0.0
                    portfolio.avg_buy_price = 0.0
        self.portfolio = portfolio

    @property
    def fee_rate_per_side(self) -> float:
        return self.settings.round_trip_fee_rate / 2

    def total_asset_krw(self, mark_price: float) -> float:
        return self.portfolio.krw_balance + (self.portfolio.usdt_balance * mark_price)

    def execute(self, signal: Signal, price: float, max_order_amount: float | None = None) -> dict | None:
        if signal == Signal.BUY:
            return self._buy(price, max_order_amount)
        if signal == Signal.SELL:
            return self._sell(price, max_order_amount)
        return None

    def _buy(self, price: float, max_order_amount: float | None) -> dict | None:
        order_limit = self.settings.max_order_amount if max_order_amount is None else max_order_amount
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
        total_asset = self.total_asset_krw(price)
        return self._insert_trade(Signal.BUY, price, volume, fee, 0.0, 0.0, total_asset)

    def _sell(self, price: float, max_order_amount: float | None) -> dict | None:
        if self.portfolio.usdt_balance <= 0:
            return None

        order_limit = self.settings.max_order_amount if max_order_amount is None else max_order_amount
        max_volume_by_amount = order_limit / price
        volume = min(self.portfolio.usdt_balance, max_volume_by_amount)
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

        total_asset = self.total_asset_krw(price)
        return self._insert_trade(Signal.SELL, price, volume, fee, profit, profit_rate, total_asset)

    def _insert_trade(
        self,
        side: Signal,
        price: float,
        volume: float,
        fee: float,
        profit: float,
        profit_rate: float,
        total_asset_krw: float,
    ) -> dict:
        created_at = utc_now_iso()
        with self.database.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO virtual_trade
                    (side, price, volume, fee, profit, profit_rate, total_asset_krw, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (side.value, price, volume, fee, profit, profit_rate, total_asset_krw, created_at),
            )
            trade_id = cursor.lastrowid
        return {
            "id": trade_id,
            "side": side.value,
            "price": price,
            "volume": volume,
            "fee": fee,
            "profit": profit,
            "profit_rate": profit_rate,
            "total_asset_krw": total_asset_krw,
            "created_at": created_at,
        }
