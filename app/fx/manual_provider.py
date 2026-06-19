from datetime import datetime, timezone

from app.config import Settings
from app.fx.provider import FxRateProvider
from app.models import FxRate


class ManualFxRateProvider(FxRateProvider):
    def __init__(self, settings: Settings):
        self.settings = settings

    async def get_usd_krw_rate(self) -> FxRate:
        return FxRate(rate=self.settings.manual_usd_krw_rate, fetched_at=datetime.now(timezone.utc))
