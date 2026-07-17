# Agent Runtime

Implements the deterministic Agent runtime: a LangGraph orchestrator over an explicit
`RunState`, a contract-enforcing tool registry, SQLite-backed events/checkpoints/evidence,
conditional branches, checkpoint recovery, human approval, replay, and a FastAPI/SSE API.

## Local startup

```powershell
python -m pip install -e ".[dev]"
uvicorn worldcup_agent.api.app:app --reload --port 8000
```

Core endpoints:

- `POST /api/runs`
- `POST /api/runs/{run_id}/start`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/initial`
- `GET /api/runs/{run_id}/events`
- `POST /api/runs/{run_id}/inject-failure`
- `POST /api/runs/{run_id}/approve`

## Regenerate the demo fixture

```powershell
python -m worldcup_agent.api.generate_fixture --output tests/fixtures/completed_run.json
```

See `docs/superpowers/plans/2026-07-15-agent-runtime-foundation.md` for the full plan.
