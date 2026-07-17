# Architecture

```text
Historical results (CC0) ──▶ Data Pipeline ──▶ Snapshot Manifest
                                                       │
                                          Elo + Goal Models + ML Calibration
                                                       │
                                              Versioned Artifacts
                                                       │
              Match Predictor ──▶ Tournament Simulator ──▶ Forecast Bundle
                                                       │
                                          Evidence Store ──▶ Agent Orchestrator
                                                       │
                                          FastAPI / SSE ──▶ Product UI + Workbench
```

## Module dependency direction

- `prediction` depends only on numpy/scipy/sklearn — never on FastAPI, LangGraph, or React.
- `tournament` consumes the `MatchPredictor` protocol; it does not know which model is selected.
- `agent` reaches domain services **only** through the contract-enforcing Tool Registry.
- `api` handles transport and error mapping; it carries no domain calculation.
- `frontend` consumes versioned JSON; it never recomputes rankings or probabilities.
- Every published number must carry an Evidence ID.

## Why the LLM never computes probabilities

The LLM parses tasks, plans steps, and explains results. All Elo ratings, score matrices, outcome probabilities, rankings, Monte Carlo counts, and backtest metrics are produced by deterministic Python. The LLM cannot invent a tool or override a sampled result. This makes the system testable, replayable, and auditable.

## Event flow

Runs are append-only event streams persisted in SQLite. The Run Snapshot is a materialized view over events. Replay reconstructs state from events without calling any tool, LLM, or simulator. SSE streams events with `Last-Event-ID` resume.

## Deployment

- Portfolio mode: `docker compose up` builds backend (uvicorn) + frontend (nginx). Backend serves `/api/*`; nginx proxies `/api` and falls back to the SPA.
- Offline mode: the committed `artifacts/demo` bundle backs all pages without a backend.
