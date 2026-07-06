from functools import lru_cache
import os
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel


class Settings(BaseModel):
    exchange: Literal["upbit", "bithumb"] = "upbit"
    market: str = "KRW-USDT"
    trade_mode: Literal["paper", "live"] = "paper"
    initial_balance: float = 100_000_000
    poll_interval_seconds: int = 10

    fx_provider: Literal["manual", "api"] = "manual"
    manual_usd_krw_rate: float = 1370.0
    fx_rate_max_stale_seconds: int = 300

    buy_premium_threshold: float = -0.3
    sell_premium_threshold: float = 0.3
    neutral_band: float = 0.1

    round_trip_fee_rate: float = 0.001
    max_order_amount: float = 10_000_000
    daily_max_trade_amount: float = 50_000_000
    daily_max_loss_rate: float = -1.0
    paper_mode_days: int = 14

    database_url: str = "sqlite:///./data/trading_bot.db"
    oracle_wallet_dir: str | None = None
    oracle_wallet_password: str | None = None
    upbit_base_url: str = "https://api.upbit.com/v1"
    bithumb_base_url: str = "https://api.bithumb.com"
    jwt_secret_key: str = "change-this-secret-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24
    encryption_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    config_path = Path("config.yml")
    if not config_path.exists():
        return Settings()

    with config_path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    env_keys = {
        "EXCHANGE",
        "DATABASE_URL",
        "ORACLE_WALLET_DIR",
        "ORACLE_WALLET_PASSWORD",
        "JWT_SECRET_KEY",
        "ENCRYPTION_KEY",
        "UPBIT_BASE_URL",
        "BITHUMB_BASE_URL",
    }
    raw.update({k.lower(): v for k, v in os.environ.items() if k in env_keys})
    return Settings(**raw)
