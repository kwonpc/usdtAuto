from datetime import datetime, timezone

import httpx

from app.fx.provider import FxRateProvider
from app.models import FxRate


class ApiFxRateProvider(FxRateProvider):
    async def get_usd_krw_rate(self) -> FxRate:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("https://open.er-api.com/v6/latest/USD")
            response.raise_for_status()
            payload = response.json()

        rate = payload.get("rates", {}).get("KRW")
        if rate is None:
            raise RuntimeError("USD/KRW rate not found in FX API response")
        return FxRate(rate=float(rate), fetched_at=datetime.now(timezone.utc))
