from __future__ import annotations

from worldcup_agent.forecasts.contracts import PublishedForecast
from worldcup_agent.forecasts.repository import ForecastRepository


class ForecastService:
    def __init__(self, repository: ForecastRepository) -> None:
        self.repository = repository

    def publish_forecast(self, forecast_id: str, run_id: str, payload: dict, versions: dict) -> PublishedForecast:
        forecast = PublishedForecast(
            forecast_id=forecast_id, run_id=run_id, payload=payload, versions=versions
        )
        self.repository.publish(forecast)
        return forecast

    def get(self, forecast_id: str) -> dict:
        return self.repository.get(forecast_id)

    def current(self) -> dict:
        return self.repository.current()
