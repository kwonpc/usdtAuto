from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models import StrategyDecision


@dataclass(frozen=True)
class StrategyContext:
    trade_price: float
    usd_krw_rate: float | None
    avg_buy_price: float
    usdt_balance: float


class TradingStrategy(ABC):
    @abstractmethod
    def decide(self, context: StrategyContext) -> StrategyDecision:
        raise NotImplementedError
