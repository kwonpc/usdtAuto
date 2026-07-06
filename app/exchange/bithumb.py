import httpx

from app.config import Settings
from app.exchange.base import ExchangeClient
from app.models import Ticker


class BithumbClient(ExchangeClient):
    def __init__(self, settings: Settings):
        self.settings = settings

    async def get_ticker(self, market: str) -> Ticker:
        async with httpx.AsyncClient(base_url=self.settings.bithumb_base_url, timeout=5.0) as client:
            ticker_response = await client.get("/v1/ticker", params={"markets": market})
            ticker_response.raise_for_status()
            ticker_payload = ticker_response.json()
            if not ticker_payload:
                raise RuntimeError(f"No ticker returned for market {market}")

            orderbook_response = await client.get("/v1/orderbook", params={"markets": market})
            orderbook_response.raise_for_status()
            orderbook_payload = orderbook_response.json()
            if not orderbook_payload:
                raise RuntimeError(f"No orderbook returned for market {market}")

        ticker = ticker_payload[0]
        orderbook = orderbook_payload[0]["orderbook_units"][0]
        return Ticker(
            market=market,
            trade_price=float(ticker["trade_price"]),
            bid_price=float(orderbook["bid_price"]),
            ask_price=float(orderbook["ask_price"]),
        )
