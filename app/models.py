from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class BotStatus(str, Enum):
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    PAUSED_BY_RISK = "PAUSED_BY_RISK"
    ERROR = "ERROR"


class TradeStatus(str, Enum):
    SIGNAL_CREATED = "SIGNAL_CREATED"
    BUY_EXECUTED = "BUY_EXECUTED"
    SELL_EXECUTED = "SELL_EXECUTED"
    ORDER_PLACED = "ORDER_PLACED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class Ticker:
    market: str
    trade_price: float
    bid_price: float
    ask_price: float


@dataclass(frozen=True)
class FxRate:
    rate: float
    fetched_at: datetime


@dataclass(frozen=True)
class StrategyDecision:
    signal: Signal
    premium_rate: float
    reason: str
