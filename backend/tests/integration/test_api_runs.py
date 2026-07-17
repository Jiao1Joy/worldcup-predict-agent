from fastapi.testclient import TestClient

from worldcup_agent.api.app import create_app
from worldcup_agent.api.routes.runs import format_sse
from worldcup_agent.domain.models import EventType, RunEvent


def test_create_run_and_fetch_snapshot(sqlite_path) -> None:
    app = create_app(sqlite_path)
    with TestClient(app) as client:
        created = client.post(
            "/api/runs",
            json={"task": "预测世界杯冠军", "seed": 7},
        )
        assert created.status_code == 201
        run_id = created.json()["run_id"]

        snapshot = client.get(f"/api/runs/{run_id}")
        assert snapshot.status_code == 200
        assert snapshot.json()["run_id"] == run_id

        initial = client.get(f"/api/runs/{run_id}/initial")
        assert initial.status_code == 200
        assert initial.json()["event_sequence"] == 0


def test_failure_injection_endpoint_recovers(sqlite_path) -> None:
    app = create_app(sqlite_path)
    with TestClient(app) as client:
        run_id = client.post("/api/runs", json={"task": "predict", "seed": 7}).json()["run_id"]
        response = client.post(
            f"/api/runs/{run_id}/inject-failure",
            json={"failure": "timeout-once"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "completed"
        assert any(item["retryable"] for item in response.json()["errors"])


def test_sse_formatter_includes_resume_id_and_event_type() -> None:
    event = RunEvent(run_id="run-1", sequence=4, event_type=EventType.RETRY, payload={"attempt": 2})

    message = format_sse(event)

    assert message.startswith("id: 4\nevent: retry\n")
    assert '"attempt":2' in message
