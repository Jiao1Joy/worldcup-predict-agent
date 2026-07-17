from __future__ import annotations

import json
from pathlib import Path

from worldcup_agent.forecasts.contracts import PublishedForecast


class ForecastRepository:
    """Persists immutable forecast read models on disk.

    Each forecast is written to ``{root}/{forecast_id}/forecast.json`` and the
    latest id is tracked in ``{root}/current.json``. Existing forecast
    directories are never overwritten.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def publish(self, forecast: PublishedForecast) -> None:
        target = self.root / forecast.forecast_id
        if target.exists():
            raise ValueError(f"forecast already published: {forecast.forecast_id}")
        target.mkdir(parents=True, exist_ok=True)
        (target / "forecast.json").write_text(
            json.dumps(forecast.payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (self.root / "current.json").write_text(
            json.dumps({"forecast_id": forecast.forecast_id}, indent=2), encoding="utf-8"
        )

    def get(self, forecast_id: str) -> dict:
        path = self.root / forecast_id / "forecast.json"
        if not path.exists():
            raise KeyError(forecast_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def current(self) -> dict:
        pointer = self.root / "current.json"
        if not pointer.exists():
            raise KeyError("no current forecast")
        forecast_id = json.loads(pointer.read_text(encoding="utf-8"))["forecast_id"]
        return self.get(forecast_id)
