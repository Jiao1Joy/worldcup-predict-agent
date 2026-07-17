# System Integration and Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate prediction, tournament, Agent, API, frontend, offline artifacts, containers, CI, documentation, and acceptance evidence into one reproducible portfolio project.

**Architecture:** Forecast bundles are persisted as immutable read models and served beside append-only Agent runs. A committed offline bundle guarantees deterministic demonstration; Docker Compose and CI exercise the same health, integrity, test, and E2E gates used for release.

**Tech Stack:** Python 3.11, FastAPI, SQLite, React/Vite, Docker Compose, GitHub Actions, pytest, Vitest, Playwright

---

## Dependencies

Complete all earlier plans before this one:

1. Agent Runtime Foundation;
2. Agent Workbench UI;
3. Prediction Engine;
4. Tournament Simulator;
5. Real LLM Agent Integration;
6. Prediction Product UI.

## File Structure

```text
backend/src/worldcup_agent/
├── forecasts/
│   ├── contracts.py
│   ├── repository.py
│   └── service.py
└── api/routes/
    ├── forecasts.py
    ├── backtests.py
    └── health.py
artifacts/demo/
├── artifact-manifest.json
├── data-manifest.json
├── rules-manifest.json
├── forecast.json
├── backtest-2022.json
├── backtest-2022-predictions.csv
├── evidence.json
└── completed-run.json
scripts/
├── verify.ps1
├── start-demo.ps1
└── smoke-test.ps1
.github/workflows/ci.yml
Dockerfile.backend
Dockerfile.frontend
compose.yaml
.env.example
README.md
docs/ZCODE_HANDOFF.md
docs/DEMO_SCRIPT.md
docs/ARCHITECTURE.md
```

## Task 1: Persist Forecast Read Models and Expose Product APIs

**Files:**
- Create: `backend/src/worldcup_agent/forecasts/contracts.py`
- Create: `backend/src/worldcup_agent/forecasts/repository.py`
- Create: `backend/src/worldcup_agent/forecasts/service.py`
- Create: `backend/src/worldcup_agent/api/routes/forecasts.py`
- Create: `backend/src/worldcup_agent/api/routes/backtests.py`
- Create: `backend/src/worldcup_agent/api/routes/health.py`
- Modify: `backend/src/worldcup_agent/api/app.py`
- Test: `backend/tests/integration/test_forecast_api.py`

- [ ] **Step 1: Write failing API contract tests**

```python
# backend/tests/integration/test_forecast_api.py
def test_current_forecast_exposes_complete_product_read_model(client, published_forecast) -> None:
    response = client.get("/api/forecasts/current")
    assert response.status_code == 200
    payload = response.json()
    assert payload["forecast_id"] == published_forecast.forecast_id
    assert len(payload["matches"]) == 104
    assert len(payload["team_probabilities"]) == 48
    assert payload["run_id"]


def test_match_and_backtest_routes_share_versions(client, published_forecast) -> None:
    match = client.get(f"/api/forecasts/{published_forecast.forecast_id}/matches/M073")
    backtest = client.get("/api/backtests/2022")
    assert match.status_code == backtest.status_code == 200
    assert match.json()["model_version"] == backtest.json()["model_version"]


def test_unknown_forecast_returns_stable_error(client) -> None:
    response = client.get("/api/forecasts/missing")
    assert response.status_code == 404
    assert response.json() == {"error_code": "forecast_not_found", "message": "Forecast was not found"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/integration/test_forecast_api.py -v`

Expected: FAIL because forecast repositories and routes do not exist.

- [ ] **Step 3: Implement immutable forecast persistence**

`ForecastRepository` stores canonical JSON under `artifacts/forecasts/{forecast_id}/` and indexes metadata in SQLite. Publishing writes to a temporary sibling directory, verifies `TournamentForecast`, Evidence coverage, backtest/model/data/rules version compatibility, then atomically renames and updates the `current` pointer. Existing forecast directories are never overwritten.

- [ ] **Step 4: Implement product routes**

Provide:

```text
GET /api/health
GET /api/artifacts/current
POST /api/forecasts
GET /api/forecasts/current
GET /api/forecasts/{forecast_id}
GET /api/forecasts/{forecast_id}/matches/{match_id}
GET /api/forecasts/{forecast_id}/bracket
GET /api/forecasts/{forecast_id}/teams
GET /api/backtests/2022
```

`POST /api/forecasts` creates an Agent run and returns `202` with `forecast_id`, `run_id`, `status_url`, and `events_url`. Read routes never trigger training, simulation, LLM, or network calls.

- [ ] **Step 5: Add error middleware**

Map domain errors to `{error_code, message, details?}`. Use codes `forecast_not_found`, `artifact_integrity_error`, `rules_integrity_error`, `validation_error`, `run_conflict`, and `internal_error`. Log a correlation ID server-side; never return tracebacks, filesystem secrets, prompts, or API keys.

- [ ] **Step 6: Run forecast API tests**

Run: `cd backend && python -m pytest tests/integration/test_forecast_api.py -v`

Expected: PASS.

- [ ] **Step 7: Commit forecast APIs**

```bash
git add backend/src/worldcup_agent/forecasts backend/src/worldcup_agent/api backend/tests/integration/test_forecast_api.py
git commit -m "feat: expose immutable forecast read models"
```

## Task 2: Generate and Verify the Offline Portfolio Bundle

**Files:**
- Create: `backend/src/worldcup_agent/cli/generate_portfolio.py`
- Create: `backend/tests/integration/test_portfolio_bundle.py`
- Create: `artifacts/demo/README.md`
- Generate: `artifacts/demo/*`

- [ ] **Step 1: Write a failing bundle-integrity test**

```python
# backend/tests/integration/test_portfolio_bundle.py
import json
from pathlib import Path


def test_committed_portfolio_bundle_is_complete_and_self_consistent() -> None:
    root = Path(__file__).parents[3] / "artifacts" / "demo"
    forecast = json.loads((root / "forecast.json").read_text(encoding="utf-8"))
    run = json.loads((root / "completed-run.json").read_text(encoding="utf-8"))
    evidence = json.loads((root / "evidence.json").read_text(encoding="utf-8"))

    assert len(forecast["matches"]) == 104
    assert len(forecast["team_probabilities"]) == 48
    assert forecast["run_id"] == run["state"]["run_id"]
    assert set(forecast["evidence_ids"]) <= {item["evidence_id"] for item in evidence}
    assert forecast["versions"]["data_version"] == run["state"]["data_snapshot"]["data_version"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && python -m pytest tests/integration/test_portfolio_bundle.py -v`

Expected: FAIL because the bundle has not been generated.

- [ ] **Step 3: Implement one deterministic bundle generator**

`worldcup-generate-portfolio --output ../artifacts/demo` loads committed miniature snapshot/artifacts/rules, runs the production Tool Registry with deterministic planner, performs 500 fixture simulations for CI speed, publishes forecast/backtest/evidence/completed-run, writes SHA-256 manifests, and sets `forecast_cutoff=2026-06-10T23:59:59Z`. It refuses to use post-cutoff match results or a live LLM.

- [ ] **Step 4: Add a fixture disclosure**

`artifacts/demo/README.md` states source, license, cutoff, reduced CI simulation count, difference from full 30,000-run rebuild, generation command, expected hashes, and that metrics are generated from included per-match rows.

- [ ] **Step 5: Generate twice and compare hashes**

Run the generator into two temporary directories with seed 20260611. Compare every canonical JSON hash; ignore only filesystem modification times. Any difference fails the task.

- [ ] **Step 6: Run the bundle test**

Run: `cd backend && python -m pytest tests/integration/test_portfolio_bundle.py -v`

Expected: PASS.

- [ ] **Step 7: Commit the offline bundle**

```bash
git add backend/src/worldcup_agent/cli/generate_portfolio.py backend/tests/integration/test_portfolio_bundle.py artifacts/demo
git commit -m "data: add deterministic portfolio forecast bundle"
```

## Task 3: Containerize Backend and Frontend

**Files:**
- Create: `Dockerfile.backend`
- Create: `Dockerfile.frontend`
- Create: `compose.yaml`
- Create: `.dockerignore`
- Create: `.env.example`
- Test: `scripts/smoke-test.ps1`

- [ ] **Step 1: Define non-root production images**

Backend uses `python:3.11-slim`, installs the package without `full-training`, copies rules and demo artifacts, creates user `app`, and runs Uvicorn on 8000. Frontend uses a Node build stage and an unprivileged Nginx runtime that proxies `/api` to backend and supports SPA fallback.

- [ ] **Step 2: Add Compose health dependencies**

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    environment:
      WORLDCUP_MODE: portfolio
      WORLDCUP_ARTIFACTS_DIR: /app/artifacts/demo
      WORLDCUP_RULES_DIR: /app/backend/rules/fifa_2026
      WORLDCUP_LLM_ENABLED: "false"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"]
      interval: 5s
      timeout: 3s
      retries: 12
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports: ["4173:8080"]
    depends_on:
      backend:
        condition: service_healthy
```

- [ ] **Step 3: Implement an external smoke test**

```powershell
# scripts/smoke-test.ps1
$ErrorActionPreference = "Stop"
$health = Invoke-RestMethod http://127.0.0.1:4173/api/health
if ($health.status -ne "ok") { throw "Backend health check failed" }
$forecast = Invoke-RestMethod http://127.0.0.1:4173/api/forecasts/current
if ($forecast.matches.Count -ne 104) { throw "Forecast does not contain 104 matches" }
$page = Invoke-WebRequest http://127.0.0.1:4173/
if ($page.StatusCode -ne 200) { throw "Frontend did not return 200" }
```

- [ ] **Step 4: Build and smoke-test containers**

Run: `docker compose build`

Expected: both images build successfully.

Run: `docker compose up -d`

Expected: backend becomes healthy and frontend starts.

Run: `powershell -ExecutionPolicy Bypass -File scripts/smoke-test.ps1`

Expected: exits 0.

- [ ] **Step 5: Stop containers**

Run: `docker compose down`

Expected: containers and network stop; forecast artifacts remain unchanged.

- [ ] **Step 6: Commit container workflow**

```bash
git add Dockerfile.backend Dockerfile.frontend compose.yaml .dockerignore .env.example scripts/smoke-test.ps1
git commit -m "build: containerize portfolio application"
```

## Task 4: Add a Single Verification Script and CI Workflow

**Files:**
- Create: `scripts/verify.ps1`
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Implement the local verification command**

```powershell
# scripts/verify.ps1
$ErrorActionPreference = "Stop"
Push-Location backend
try {
  python -m pytest -q
  python -m ruff check src tests
} finally { Pop-Location }
Push-Location frontend
try {
  npm ci
  npm test
  npm run build
  npm run e2e
} finally { Pop-Location }
```

- [ ] **Step 2: Add deterministic CI jobs**

The workflow uses Windows or Ubuntu consistently with path-safe commands, Python 3.11, Node 20, npm cache, pip cache, Chromium install, backend tests, Ruff, frontend tests, build, E2E, portfolio-bundle integrity, and Docker build. It never enables live LLM or downloads a mutable training dataset.

- [ ] **Step 3: Upload useful failure artifacts**

On failure upload pytest JUnit XML, Playwright report/screenshots/traces, frontend build logs, and artifact manifest diagnostics. Never upload `.env`, SQLite files containing prompts, or API keys.

- [ ] **Step 4: Run the verification script locally**

Run: `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1`

Expected: backend tests/Ruff, frontend tests/build/E2E all exit 0.

- [ ] **Step 5: Commit CI**

```bash
git add scripts/verify.ps1 .github/workflows/ci.yml
git commit -m "ci: verify complete forecast application"
```

## Task 5: Add Security, Privacy, and Data-License Checks

**Files:**
- Create: `backend/tests/security/test_redaction.py`
- Create: `docs/DATA_SOURCES.md`
- Create: `docs/SECURITY.md`
- Modify: `.gitignore`

- [ ] **Step 1: Write failing redaction tests**

Create tests that put a fake API key, authorization header, raw prompt, and filesystem home path into an LLM/tool error. Assert logs, API responses, RunEvent payloads, and completed-run fixtures contain none of those values. Assert the safe event retains error type, retryability, provider, attempt, and correlation ID.

- [ ] **Step 2: Run redaction tests to verify they fail**

Run: `cd backend && python -m pytest tests/security/test_redaction.py -v`

Expected: FAIL until shared redaction is applied to logging and events.

- [ ] **Step 3: Apply centralized redaction**

Add a recursive redactor for keys matching `api_key`, `authorization`, `token`, `secret`, `prompt`, and known configured secret values. Apply it before logging, event persistence, HTTP error serialization, and fixture generation.

- [ ] **Step 4: Document source and model obligations**

`DATA_SOURCES.md` records martj42 source URL/license, FIFA rule URLs, retrieval dates, hashes, redistribution status, fixture attribution, and rebuild instructions. `SECURITY.md` documents secrets, outbound hosts, prompt retention, event redaction, dependency updates, and how to report a vulnerability.

- [ ] **Step 5: Protect generated and secret files**

`.gitignore` excludes `.env`, non-demo SQLite databases, raw downloads, generated full model binaries, Playwright secrets, and local caches. It explicitly allows `.env.example`, official rule files, miniature fixtures, and `artifacts/demo` manifests.

- [ ] **Step 6: Run security tests**

Run: `cd backend && python -m pytest tests/security/test_redaction.py -v`

Expected: PASS.

- [ ] **Step 7: Commit security documentation**

```bash
git add backend/tests/security docs/DATA_SOURCES.md docs/SECURITY.md .gitignore
git commit -m "docs: secure and attribute forecast data"
```

## Task 6: Write the Final Handoff, Architecture, and Demo Documentation

**Files:**
- Replace: `README.md`
- Create: `docs/ZCODE_HANDOFF.md`
- Create: `docs/ARCHITECTURE.md`
- Create: `docs/DEMO_SCRIPT.md`
- Create: `scripts/start-demo.ps1`

- [ ] **Step 1: Replace the placeholder README**

README order:

1. one-sentence value proposition and screenshot;
2. champion forecast disclaimer and frozen cutoff;
3. feature list for prediction, tournament, Agent, and UI;
4. architecture diagram;
5. three-command Portfolio quick start;
6. tests and rebuild commands;
7. data/model/rules versions;
8. documentation index;
9. limitations and license.

- [ ] **Step 2: Add a fail-fast demo launcher**

```powershell
# scripts/start-demo.ps1
$ErrorActionPreference = "Stop"
docker compose up -d --build
& "$PSScriptRoot\smoke-test.ps1"
Write-Host "World Cup Prediction Agent: http://127.0.0.1:4173"
```

- [ ] **Step 3: Write the six-minute demo script**

`DEMO_SCRIPT.md` contains timed actions: champion result, tournament tree, match score matrix, 2022 backtest, Agent graph, dynamic simulate-more branch, injected timeout recovery, Evidence, Replay, architecture/tests, and limitations. Every click target matches a real route or accessible label.

- [ ] **Step 4: Write architecture and handoff docs**

`ARCHITECTURE.md` shows module dependency arrows, data flow, event flow, artifact flow, deployment, and why LLM never computes probabilities. `ZCODE_HANDOFF.md` lists exact plan order, completion gate for each, source-of-truth priority, commands, files never to overwrite, permitted assumptions, and stop conditions.

- [ ] **Step 5: Verify every documented command exists**

Search README and docs for command blocks. Run every local command that does not require a full training dataset or API key. Commands requiring external data must provide a fixture alternative and explicit expected artifact names.

- [ ] **Step 6: Commit final documentation**

```bash
git add README.md docs/ZCODE_HANDOFF.md docs/ARCHITECTURE.md docs/DEMO_SCRIPT.md scripts/start-demo.ps1
git commit -m "docs: complete project handoff and demo guide"
```

## Task 7: Execute the Final Acceptance Matrix

**Files:**
- Create: `docs/ACCEPTANCE_REPORT.md`

- [ ] **Step 1: Verify repository integrity**

Run: `git status --short`

Expected: empty before acceptance begins.

Run: `powershell -ExecutionPolicy Bypass -File scripts/verify.ps1`

Expected: all automated gates exit 0.

- [ ] **Step 2: Verify domain invariants**

Record test evidence for cutoff leakage, matrix normalization, outcome reconciliation, artifact hashes, 495 Annexe C combinations, 104 matches, unique champion, fixed-seed hash, and champion probability sum.

- [ ] **Step 3: Verify Agent invariants**

Record no-key completion, fixed provider ID, structured response validation, dynamic branch, retry/checkpoint recovery, approval, 100% Evidence coverage, and zero external calls during Replay.

- [ ] **Step 4: Verify product journeys**

Record desktop and 390px viewport results for Overview → Tournament → Match Detail → Agent Workbench, Backtest integrity, offline mode, and no horizontal overflow.

- [ ] **Step 5: Verify container smoke test**

Build, start, smoke-test, and stop Compose. Record image IDs, health result, current forecast ID, and HTTP status without embedding environment secrets.

- [ ] **Step 6: Write the acceptance report**

For every criterion, write `PASS`, `FAIL`, or `NOT RUN`, exact command, date, commit SHA, and evidence path. Never mark unexecuted full-training or live-LLM tests as PASS. A release is complete only when all required Portfolio criteria are PASS; optional Full Training and Live LLM may be NOT RUN with reasons.

- [ ] **Step 7: Commit acceptance evidence**

```bash
git add docs/ACCEPTANCE_REPORT.md
git commit -m "test: record complete portfolio acceptance"
```

## System Completion Gate

- `README.md` is no longer a placeholder;
- Portfolio bundle passes hashes and cross-file version checks;
- Forecast APIs are read-only for reads and use stable errors;
- backend tests and Ruff pass;
- frontend tests, build, and E2E pass;
- Compose builds, becomes healthy, serves 104-match forecast, and stops cleanly;
- security redaction tests pass;
- source licenses and provenance are documented;
- acceptance report distinguishes PASS from NOT RUN honestly;
- a fresh Coding Agent can follow `docs/ZCODE_HANDOFF.md` without relying on conversation history.
