from abc import ABC, abstractmethod

from app.models import Ticker


class ExchangeClient(ABC):
    @abstractmethod
    async def get_ticker(self, market: str) -> Ticker:
        raise NotImplementedError
