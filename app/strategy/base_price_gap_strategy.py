from app.models import Signal, StrategyDecision
from app.strategy.base import StrategyContext, TradingStrategy


class BasePriceGapStrategy(TradingStrategy):
    def __init__(self, base_price: float | None, price_gap: float):
        self.base_price = base_price
        self.price_gap = price_gap

    def decide(self, context: StrategyContext) -> StrategyDecision:
        if self.base_price is None:
            return StrategyDecision(Signal.HOLD, None, "Base price is not configured")

        buy_trigger = self.base_price - self.price_gap
        if context.usdt_balance <= 0 and context.trade_price <= buy_trigger:
            return StrategyDecision(Signal.BUY, None, "Current price reached base-price buy trigger")

        sell_trigger = context.avg_buy_price + self.price_gap
        if context.usdt_balance > 0 and context.trade_price >= sell_trigger:
            return StrategyDecision(Signal.SELL, None, "Current price reached average-buy sell trigger")

        return StrategyDecision(Signal.HOLD, None, "Current price is inside base-price gap range")
