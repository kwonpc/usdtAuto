from app.config import Settings
from app.models import Signal, StrategyDecision


def calculate_premium_rate(upbit_usdt_price: float, usd_krw_rate: float) -> float:
    return ((upbit_usdt_price / usd_krw_rate) - 1) * 100


class PremiumRebalanceStrategy:
    def __init__(self, settings: Settings):
        self.settings = settings

    def decide(self, upbit_usdt_price: float, usd_krw_rate: float) -> StrategyDecision:
        premium_rate = calculate_premium_rate(upbit_usdt_price, usd_krw_rate)
        if premium_rate <= self.settings.buy_premium_threshold:
            return StrategyDecision(Signal.BUY, premium_rate, "USDT undervalued against USD/KRW")
        if premium_rate >= self.settings.sell_premium_threshold:
            return StrategyDecision(Signal.SELL, premium_rate, "USDT overvalued against USD/KRW")
        return StrategyDecision(Signal.HOLD, premium_rate, "Premium is inside no-trade range")
