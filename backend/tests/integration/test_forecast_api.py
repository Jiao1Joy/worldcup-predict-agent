from fastapi.testclient import TestClient

from worldcup_agent.api.app import create_app
from worldcup_agent.forecasts.repository import ForecastRepository
from worldcup_agent.forecasts.service import ForecastService


def _client_with_forecast(tmp_path, forecast_payload):
    repo = ForecastRepository(tmp_path / "forecasts")
    service = ForecastService(repo)
    service.publish_forecast(
        forecast_id=forecast_payload["forecast_id"],
        run_id="run-1",
        payload=forecast_payload,
        versions=forecast_payload.get("versions", {}),
    )
    app = create_app(tmp_path / "api.sqlite3", mode="demo", forecasts_dir=tmp_path / "forecasts")
    return app


def test_current_forecast_exposes_complete_product_read_model(tmp_path) -> None:
    payload = {
        "forecast_id": "fc-test",
        "matches": [{"match_id": f"M{i:03d}"} for i in range(1, 105)],
        "team_probabilities": {f"Team{i}": {"champion": 0.01} for i in range(48)},
        "run_id": "run-1",
    }
    app = _client_with_forecast(tmp_path, payload)
    with TestClient(app) as client:
        response = client.get("/api/forecasts/current")
    assert response.status_code == 200
    body = response.json()
    assert body["forecast_id"] == "fc-test"
    assert len(body["matches"]) == 104


def test_unknown_forecast_returns_stable_error(tmp_path) -> None:
    app = _client_with_forecast(tmp_path, {"forecast_id": "fc-test", "matches": []})
    with TestClient(app) as client:
        response = client.get("/api/forecasts/missing")
    assert response.status_code == 404


def test_health_endpoint(tmp_path) -> None:
    app = create_app(tmp_path / "h.sqlite3", mode="demo")
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
