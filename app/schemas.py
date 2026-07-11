from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    login_id: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=100)


class LoginRequest(BaseModel):
    login_id: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    login_id: str


class ApiKeyCreateRequest(BaseModel):
    exchange: Literal["upbit", "bithumb"] = "upbit"
    name: str = Field(min_length=1, max_length=100)
    access_key: str = Field(min_length=1)
    secret_key: str = Field(min_length=1)


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    is_active: bool
    created_at: datetime


class BotSettingsRequest(BaseModel):
    exchange: Literal["upbit", "bithumb"] = "upbit"
    market: str = "KRW-USDT"
    trade_mode: Literal["paper", "live"] = "paper"
    strategy_type: Literal["premium_rebalance", "base_price_gap"] = "premium_rebalance"
    api_key_id: int | None = None
    buy_premium_threshold: float = -0.3
    sell_premium_threshold: float = 0.3
    neutral_band: float = 0.1
    base_price: float | None = None
    price_gap: float = 3.0
    round_trip_fee_rate: float = 0.001
    max_order_amount: float = 10_000_000
    daily_max_trade_amount: float = 50_000_000
    daily_max_loss_rate: float = -1.0
    base_loss_cut_price: float | None = None
    fx_provider: Literal["manual", "api"] = "manual"
    manual_usd_krw_rate: float = 1370.0
    fx_rate_max_stale_seconds: int = 300


class ManualSellRequest(BaseModel):
    price: float = Field(gt=0)
    volume: float | None = Field(default=None, gt=0)


class BotResponse(BaseModel):
    id: int
    name: str
    exchange: str
    market: str
    trade_mode: str
    strategy_type: str
    bot_status: str


class StatusResponse(BaseModel):
    botStatus: str
    exchange: str
    tradeMode: str
    strategyType: str
    exchangeUsdtPrice: float
    upbitUsdtPrice: float
    usdKrwRate: float | None
    premiumRate: float | None
    krwBalance: float
    usdtBalance: float
    avgBuyPrice: float
    totalAssetKrw: float
    todayTradeCount: int
    todayProfit: float
    lastSignal: str
    lastSignalAt: str | None
    lastError: str | None
