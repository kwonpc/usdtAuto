from app.config import Settings
from app.exchange.base import ExchangeClient
from app.exchange.bithumb import BithumbClient
from app.exchange.upbit import UpbitClient


def create_exchange_client(exchange: str, settings: Settings) -> ExchangeClient:
    if exchange == "bithumb":
        return BithumbClient(settings)
    if exchange == "upbit":
        return UpbitClient(settings)
    raise ValueError(f"Unsupported exchange: {exchange}")
