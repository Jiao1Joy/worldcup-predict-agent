from fastapi.testclient import TestClient

from worldcup_agent.api.app import create_app


def test_application_completes_forecast_without_llm_key(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("WORLDCUP_LLM_API_KEY", raising=False)
    app = create_app(tmp_path / "fallback.sqlite3", mode="production")
    with TestClient(app) as client:
        run_id = client.post("/api/runs", json={"task": "预测世界杯冠军", "seed": 7}).json()["run_id"]
        response = client.post(f"/api/runs/{run_id}/start")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
