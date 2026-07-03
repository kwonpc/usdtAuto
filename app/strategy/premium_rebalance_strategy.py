from app.config import Settings
from app.models import Signal, StrategyDecision
from app.strategy.base import StrategyContext, TradingStrategy


def calculate_premium_rate(upbit_usdt_price: float, usd_krw_rate: float) -> float:
    return ((upbit_usdt_price / usd_krw_rate) - 1) * 100


class PremiumRebalanceStrategy(TradingStrategy):
    def __init__(self, buy_threshold: float, sell_threshold: float):
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold

    def decide(self, context: StrategyContext) -> StrategyDecision:
        if context.usd_krw_rate is None:
            return StrategyDecision(Signal.HOLD, None, "USD/KRW rate is not available")
        premium_rate = calculate_premium_rate(context.trade_price, context.usd_krw_rate)
        if premium_rate <= self.buy_threshold:
            return StrategyDecision(Signal.BUY, premium_rate, "USDT undervalued against USD/KRW")
        if premium_rate >= self.sell_threshold:
            return StrategyDecision(Signal.SELL, premium_rate, "USDT overvalued against USD/KRW")
        return StrategyDecision(Signal.HOLD, premium_rate, "Premium is inside no-trade range")
