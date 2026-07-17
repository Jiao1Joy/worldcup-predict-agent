from __future__ import annotations

from pydantic import BaseModel


class PublishedForecast(BaseModel):
    forecast_id: str
    run_id: str
    payload: dict
    versions: dict
