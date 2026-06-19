from abc import ABC, abstractmethod

from app.models import FxRate


class FxRateProvider(ABC):
    @abstractmethod
    async def get_usd_krw_rate(self) -> FxRate:
        raise NotImplementedError
