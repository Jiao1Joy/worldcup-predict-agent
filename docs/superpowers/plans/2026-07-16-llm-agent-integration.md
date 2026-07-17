# Real LLM Agent Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace product-facing demo tools with real prediction and tournament adapters, add a provider-neutral structured LLM Orchestrator, and preserve deterministic fallback, evidence validation, recovery, and replay.

**Architecture:** Domain services remain deterministic and expose strict Tool Contracts. An OpenAI-compatible provider adapter returns schema-validated TaskSpec, decisions, and explanations; LangGraph routes those decisions, while a deterministic planner guarantees full operation without an API key.

**Tech Stack:** Python 3.11, FastAPI, Pydantic 2, LangGraph, httpx, pytest, respx

---

## Dependencies

Complete and verify:

1. `docs/superpowers/plans/2026-07-15-agent-runtime-foundation.md`;
2. `docs/superpowers/plans/2026-07-16-prediction-engine.md`;
3. `docs/superpowers/plans/2026-07-16-tournament-simulator.md`.

The Agent Runtime may keep `tools/demo.py` for unit tests and offline failure scenarios, but `api/dependencies.py` must stop using `build_demo_registry()` in the product application.

## File Structure

```text
backend/src/worldcup_agent/
├── llm/
│   ├── contracts.py
│   ├── config.py
│   ├── openai_compatible.py
│   ├── prompts.py
│   └── fallback.py
├── agent/
│   ├── task_parser.py
│   ├── planner.py
│   ├── explainer.py
│   └── publisher.py
├── tools/
│   ├── forecast.py
│   └── production.py
├── runtime/
│   ├── orchestrator.py
│   └── service.py
└── api/
    ├── dependencies.py
    └── app.py
backend/tests/
├── unit/llm/
├── unit/agent/
└── integration/
    ├── test_real_tool_run.py
    ├── test_llm_fallback.py
    └── test_evidence_publish.py
```

## Task 1: Adapt Real Domain Services to Tool Contracts

**Files:**
- Create: `backend/src/worldcup_agent/tools/forecast.py`
- Create: `backend/src/worldcup_agent/tools/production.py`
- Test: `backend/tests/integration/test_real_tool_run.py`

- [ ] **Step 1: Write a failing production-registry test**

```python
# backend/tests/integration/test_real_tool_run.py
from worldcup_agent.tools.contracts import ToolContext
from worldcup_agent.tools.production import build_production_registry


async def test_production_registry_runs_real_forecast_services(runtime_services) -> None:
    registry = build_production_registry(runtime_services)
    context = ToolContext(run_id="run-1", step_id="simulate")

    snapshot = await registry.execute("inspect_snapshot", {}, context)
    forecast = await registry.execute(
        "simulate_tournament",
        {"runs": 500, "seed": 7, "as_of": "2026-06-10T23:59:59Z"},
        context,
    )

    assert snapshot.output["data_version"] == runtime_services.data_version
    assert forecast.output["forecast_id"]
    assert len(forecast.output["matches"]) == 104
    assert forecast.output["provider"] != "demo-simulator"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && python -m pytest tests/integration/test_real_tool_run.py -v`

Expected: FAIL because production tool adapters do not exist.

- [ ] **Step 3: Define tool input and output models**

```python
# backend/src/worldcup_agent/tools/forecast.py
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class InspectSnapshotInput(BaseModel):
    expected_data_version: str | None = None


class InspectSnapshotOutput(BaseModel):
    data_version: str
    model_version: str
    rules_version: str
    snapshot_cutoff: datetime
    compatible: bool


class SimulateTournamentInput(BaseModel):
    runs: int = Field(ge=100, le=100_000)
    seed: int
    as_of: datetime


class SimulateTournamentOutput(BaseModel):
    forecast_id: str
    matches: list[dict[str, Any]]
    team_probabilities: dict[str, Any]
    probability_delta: float
    evidence_ids: list[str]
    provider: str = "tournament-service"
```

- [ ] **Step 4: Build adapters by dependency injection**

`ProductionServices` contains snapshot repository, artifact repository, `PredictionService`, `TournamentForecastService`, and Evidence Store. `build_production_registry(services)` registers `inspect_snapshot`, `predict_match`, `simulate_tournament`, `load_backtest`, and `retrieve_evidence`. Each handler validates versions before computing, persists returned evidence, and returns only JSON-serializable Pydantic output. No handler imports FastAPI or an LLM provider.

- [ ] **Step 5: Run production tool tests**

Run: `cd backend && python -m pytest tests/integration/test_real_tool_run.py -v`

Expected: PASS.

- [ ] **Step 6: Commit production tool adapters**

```bash
git add backend/src/worldcup_agent/tools backend/tests/integration/test_real_tool_run.py
git commit -m "feat: expose real forecast agent tools"
```

## Task 2: Define Provider-Neutral Structured LLM Contracts

**Files:**
- Create: `backend/src/worldcup_agent/llm/contracts.py`
- Create: `backend/src/worldcup_agent/llm/config.py`
- Test: `backend/tests/unit/llm/test_contracts.py`

- [ ] **Step 1: Write failing secret and configuration tests**

```python
# backend/tests/unit/llm/test_contracts.py
from worldcup_agent.llm.config import LLMSettings


def test_settings_redact_api_key() -> None:
    settings = LLMSettings(
        enabled=True,
        base_url="https://provider.example/v1",
        api_key="secret-value",
        model="fixed-model-id",
    )
    assert "secret-value" not in repr(settings)
    assert settings.model == "fixed-model-id"


def test_missing_key_disables_live_provider(monkeypatch) -> None:
    monkeypatch.delenv("WORLDCUP_LLM_API_KEY", raising=False)
    settings = LLMSettings.from_env()
    assert settings.enabled is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/llm/test_contracts.py -v`

Expected: FAIL because LLM contracts do not exist.

- [ ] **Step 3: Implement settings and request contracts**

```python
# backend/src/worldcup_agent/llm/contracts.py
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

ResponseT = TypeVar("ResponseT", bound=BaseModel)


class StructuredRequest(BaseModel):
    system_prompt: str
    user_payload: dict[str, Any]
    prompt_version: str
    temperature: float = 0.0


class LLMUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class StructuredResponse(BaseModel):
    value: BaseModel
    provider: str
    model: str
    usage: LLMUsage


class LLMProvider(Protocol):
    async def complete_structured(self, request: StructuredRequest, response_model: type[ResponseT]) -> StructuredResponse: ...
```

`config.py` implements `LLMSettings` with `SecretStr`, environment names `WORLDCUP_LLM_ENABLED`, `WORLDCUP_LLM_BASE_URL`, `WORLDCUP_LLM_API_KEY`, `WORLDCUP_LLM_MODEL`, `WORLDCUP_LLM_TIMEOUT_SECONDS`, and `WORLDCUP_LLM_MAX_RETRIES`. Reject model names equal to `latest`; require an explicit model identifier when enabled.

- [ ] **Step 4: Run contract tests**

Run: `cd backend && python -m pytest tests/unit/llm/test_contracts.py -v`

Expected: PASS.

- [ ] **Step 5: Commit LLM contracts**

```bash
git add backend/src/worldcup_agent/llm backend/tests/unit/llm/test_contracts.py
git commit -m "feat: define provider neutral llm contracts"
```

## Task 3: Implement the OpenAI-Compatible Adapter

**Files:**
- Create: `backend/src/worldcup_agent/llm/openai_compatible.py`
- Modify: `backend/pyproject.toml`
- Test: `backend/tests/unit/llm/test_openai_compatible.py`

- [ ] **Step 1: Add the mock HTTP dependency**

Add to the existing `dev` extra:

```toml
"respx>=0.22,<1",
```

- [ ] **Step 2: Write failing response and repair tests**

```python
# backend/tests/unit/llm/test_openai_compatible.py
import httpx
import respx
from pydantic import BaseModel

from worldcup_agent.llm.openai_compatible import OpenAICompatibleProvider


class Choice(BaseModel):
    action: str


@respx.mock
async def test_adapter_parses_structured_json(settings, structured_request) -> None:
    respx.post("https://provider.example/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={
            "choices": [{"message": {"content": '{"action":"simulate"}'}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 4},
        })
    )
    provider = OpenAICompatibleProvider(settings)
    response = await provider.complete_structured(structured_request, Choice)
    assert response.value.action == "simulate"
    assert response.usage.input_tokens == 10
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/llm/test_openai_compatible.py -v`

Expected: FAIL because the adapter does not exist.

- [ ] **Step 4: Implement HTTP, schema, timeout, and one repair attempt**

The adapter posts to `{base_url}/chat/completions` with `model`, system/user messages, `temperature`, and `response_format` JSON schema when supported. Parse `choices[0].message.content`, validate with the supplied Pydantic model, and return usage. On timeout or HTTP 429/5xx, retry according to settings with bounded exponential backoff. On validation failure, make exactly one repair request containing only the validation errors and original JSON; never include API keys, Python traces, or hidden reasoning in prompts or logs.

Raise typed `LLMUnavailableError`, `LLMResponseValidationError`, or `LLMRateLimitError` with safe summaries.

- [ ] **Step 5: Add invalid JSON and timeout tests**

Test that invalid JSON followed by valid repaired JSON makes two calls, persistent invalid JSON raises `LLMResponseValidationError`, HTTP 401 is not retried, and timeout attempts equal `max_retries + 1`.

- [ ] **Step 6: Run adapter tests**

Run: `cd backend && python -m pytest tests/unit/llm/test_openai_compatible.py -v`

Expected: PASS.

- [ ] **Step 7: Commit the provider adapter**

```bash
git add backend/pyproject.toml backend/src/worldcup_agent/llm/openai_compatible.py backend/tests/unit/llm/test_openai_compatible.py
git commit -m "feat: call openai compatible llm providers"
```

## Task 4: Implement Task Parsing and Structured Planning

**Files:**
- Create: `backend/src/worldcup_agent/agent/task_parser.py`
- Create: `backend/src/worldcup_agent/agent/planner.py`
- Create: `backend/src/worldcup_agent/llm/prompts.py`
- Create: `backend/src/worldcup_agent/llm/fallback.py`
- Test: `backend/tests/unit/agent/test_planner.py`

- [ ] **Step 1: Write failing live and fallback planner tests**

```python
# backend/tests/unit/agent/test_planner.py
from worldcup_agent.agent.planner import AgentPlanner, TaskSpec


async def test_parser_returns_typed_task(fake_provider) -> None:
    planner = AgentPlanner(fake_provider)
    spec = await planner.parse("预测冻结赛前快照的世界杯冠军")
    assert spec.intent == "predict_tournament"
    assert spec.mode == "portfolio_frozen"


async def test_fallback_plan_is_complete_without_provider() -> None:
    planner = AgentPlanner(provider=None)
    plan = await planner.plan(TaskSpec(intent="predict_tournament", mode="portfolio_frozen"))
    assert plan.steps == [
        "inspect_snapshot", "ensure_artifacts", "predict_matches",
        "simulate_tournament", "critique", "explain", "publish",
    ]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/agent/test_planner.py -v`

Expected: FAIL because planner modules do not exist.

- [ ] **Step 3: Define typed planner outputs**

```python
# backend/src/worldcup_agent/agent/planner.py
from typing import Literal

from pydantic import BaseModel, Field


class TaskSpec(BaseModel):
    intent: Literal["predict_match", "predict_tournament", "inspect_backtest"]
    mode: Literal["portfolio_frozen", "rebuild", "as_of"]
    as_of: str | None = None
    simulation_runs: int = Field(default=30_000, ge=100, le=100_000)
    explain_level: Literal["summary", "evidence"] = "evidence"
    allow_human_review: bool = True


class ExecutionPlan(BaseModel):
    steps: list[str]
    reason: str
    prompt_version: str | None = None
```

`prompts.py` contains versioned templates `task-parser-v1`, `planner-v1`, and `explainer-v1`. Planner prompts explicitly state: never calculate a probability, never invent a tool, never reveal hidden reasoning, and return only schema-conforming JSON.

- [ ] **Step 4: Implement deterministic fallback**

`fallback.py` maps each intent to an allowlisted step sequence. `AgentPlanner` uses the provider when configured, validates every returned step against the Tool Registry, and falls back when the provider is absent or raises `LLMUnavailableError`. Invalid or unauthorized steps are blocking validation errors, not silently executed.

- [ ] **Step 5: Run planner tests**

Run: `cd backend && python -m pytest tests/unit/agent/test_planner.py -v`

Expected: PASS.

- [ ] **Step 6: Commit planning**

```bash
git add backend/src/worldcup_agent/agent backend/src/worldcup_agent/llm backend/tests/unit/agent/test_planner.py
git commit -m "feat: plan forecast runs with structured llm output"
```

## Task 5: Generate Evidence-Bound Explanations

**Files:**
- Create: `backend/src/worldcup_agent/agent/explainer.py`
- Create: `backend/src/worldcup_agent/agent/publisher.py`
- Test: `backend/tests/integration/test_evidence_publish.py`

- [ ] **Step 1: Write a failing hallucinated-number rejection test**

```python
# backend/tests/integration/test_evidence_publish.py
import pytest

from worldcup_agent.agent.explainer import Explanation, ExplanationClaim
from worldcup_agent.agent.publisher import publish_explanation
from worldcup_agent.domain.errors import EvidenceValidationError


def test_publish_rejects_number_not_present_in_evidence(evidence_bundle) -> None:
    explanation = Explanation(
        summary="Team A is favourite",
        claims=[ExplanationClaim(text="Team A has 99% chance", value=0.99, evidence_id="FORECAST-1")],
        uncertainty="Predictions are probabilistic.",
    )
    with pytest.raises(EvidenceValidationError, match="claim value mismatch"):
        publish_explanation(explanation, evidence_bundle)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && python -m pytest tests/integration/test_evidence_publish.py -v`

Expected: FAIL because explanation and publisher modules do not exist.

- [ ] **Step 3: Implement explanation schemas and template fallback**

`ExplanationClaim` contains `text`, optional numeric `value`, `unit`, and `evidence_id`. `Explanation` contains champion conclusion, three to six claims, uncertainty, data/model/rules versions, and `decision_records`; it contains no `thoughts`, `chain_of_thought`, or HTML. The fallback explainer selects the top champion probability, convergence delta, strongest match path, and backtest RPS from Evidence and renders fixed templates.

- [ ] **Step 4: Validate every numeric claim before publishing**

`publish_explanation` verifies Evidence existence, version compatibility, numeric equality using evidence-specific tolerance, 100% claim coverage, and a non-empty uncertainty disclosure. It stores only the validated structured explanation and a rendered Markdown summary. Failed validation emits a Guardrail event and never creates the published forecast read model.

- [ ] **Step 5: Run evidence tests**

Run: `cd backend && python -m pytest tests/integration/test_evidence_publish.py tests/unit/test_evidence.py -v`

Expected: PASS.

- [ ] **Step 6: Commit evidence-bound explanations**

```bash
git add backend/src/worldcup_agent/agent backend/tests/integration/test_evidence_publish.py
git commit -m "feat: publish evidence bound explanations"
```

## Task 6: Integrate the Real Graph and Dynamic Policies

**Files:**
- Modify: `backend/src/worldcup_agent/runtime/orchestrator.py`
- Modify: `backend/src/worldcup_agent/runtime/policies.py`
- Modify: `backend/src/worldcup_agent/runtime/service.py`
- Test: `backend/tests/integration/test_real_agent_graph.py`

- [ ] **Step 1: Write a failing real-graph trace test**

```python
# backend/tests/integration/test_real_agent_graph.py
from worldcup_agent.runtime.service import AgentRuntimeService


async def test_real_run_publishes_forecast_and_trace(runtime_store, production_registry, fallback_planner) -> None:
    service = AgentRuntimeService(runtime_store, production_registry, planner=fallback_planner)
    run = await service.create_run({"task": "预测世界杯冠军", "mode": "portfolio_frozen"})
    completed = await service.run(run.run_id)
    events = await runtime_store.list_events(run.run_id)

    assert completed.status.value == "completed"
    assert completed.tournament_state["matches_count"] == 104
    assert completed.evidence_refs
    assert {event.step_id for event in events} >= {"inspect_snapshot", "simulate_tournament", "critique", "explain", "publish"}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && python -m pytest tests/integration/test_real_agent_graph.py -v`

Expected: FAIL because the runtime still contains the demo graph signature.

- [ ] **Step 3: Replace the fixed demo graph with planned steps**

Build nodes for parse, inspect_snapshot, ensure_artifacts, predict_matches, simulate_tournament, critique, explain, and publish. Each node calls only a registered tool or injected Agent service, emits Tool and State events, and persists a checkpoint after snapshot, artifact load, every simulation batch, and before publish.

Policies must implement these exact branches:

```python
def snapshot_policy(age_hours: float, versions_match: bool) -> str:
    if not versions_match:
        return "human_approval"
    return "refresh_snapshot" if age_hours > 24 else "ensure_artifacts"


def simulation_policy(delta: float, total_runs: int) -> str:
    return "simulate_more" if delta > 0.005 and total_runs < 50_000 else "critique"


def evidence_policy(coverage: float, versions_match: bool) -> str:
    return "repair_evidence" if coverage < 1.0 or not versions_match else "publish"
```

- [ ] **Step 4: Preserve replay compatibility**

Keep existing event types and append new payload fields without renaming old fields. Replay must reconstruct the same final `RunState` hash without calling prediction, LLM, or tournament services.

- [ ] **Step 5: Run graph and replay tests**

Run: `cd backend && python -m pytest tests/integration/test_real_agent_graph.py tests/integration/test_replay.py tests/integration/test_checkpoint_recovery.py -v`

Expected: PASS.

- [ ] **Step 6: Commit graph integration**

```bash
git add backend/src/worldcup_agent/runtime backend/tests/integration/test_real_agent_graph.py
git commit -m "feat: orchestrate real tournament forecast tools"
```

## Task 7: Wire Production Dependencies and Failure Degradation

**Files:**
- Modify: `backend/src/worldcup_agent/api/dependencies.py`
- Modify: `backend/src/worldcup_agent/api/app.py`
- Create: `backend/tests/integration/test_llm_fallback.py`
- Create: `backend/.env.example`
- Create: `backend/docs/LLM_AGENT.md`

- [ ] **Step 1: Write a failing no-key fallback test**

```python
# backend/tests/integration/test_llm_fallback.py
def test_application_completes_forecast_without_llm_key(app_factory, monkeypatch) -> None:
    monkeypatch.delenv("WORLDCUP_LLM_API_KEY", raising=False)
    with app_factory() as client:
        run_id = client.post("/api/runs", json={"task": "预测世界杯冠军", "seed": 7}).json()["run_id"]
        response = client.post(f"/api/runs/{run_id}/start")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["task_spec"]["planner"] == "deterministic"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && python -m pytest tests/integration/test_llm_fallback.py -v`

Expected: FAIL because application dependencies still build the demo registry.

- [ ] **Step 3: Build production services at application lifespan**

Load and hash-check rules, data manifest, and model artifacts once. Construct PredictionService, TournamentForecastService, Evidence Store, production Tool Registry, LLM settings, optional provider, AgentPlanner, and AgentRuntimeService. Fail startup on invalid artifacts or Annexe C; do not fail startup solely because the LLM key is absent.

- [ ] **Step 4: Add safe environment documentation**

```dotenv
WORLDCUP_MODE=portfolio
WORLDCUP_ARTIFACTS_DIR=../artifacts/demo
WORLDCUP_RULES_DIR=rules/fifa_2026
WORLDCUP_LLM_ENABLED=false
WORLDCUP_LLM_BASE_URL=https://api.example.com/v1
WORLDCUP_LLM_API_KEY=
WORLDCUP_LLM_MODEL=fixed-model-id
WORLDCUP_LLM_TIMEOUT_SECONDS=30
WORLDCUP_LLM_MAX_RETRIES=2
```

- [ ] **Step 5: Add chaos cases**

Test LLM timeout, 429, invalid JSON, missing key, tool timeout, evidence mismatch, artifact mismatch, and approval pause. Only artifact/rule/evidence integrity failures are blocking; provider failures degrade to deterministic behavior and emit a Guardrail event.

- [ ] **Step 6: Run the Agent integration completion gate**

Run: `cd backend && python -m pytest tests/unit/llm tests/unit/agent tests/integration/test_real_tool_run.py tests/integration/test_evidence_publish.py tests/integration/test_real_agent_graph.py tests/integration/test_llm_fallback.py -q`

Expected: all tests PASS.

Run: `cd backend && python -m ruff check src tests`

Expected: Ruff reports no errors.

- [ ] **Step 7: Commit production wiring**

```bash
git add backend/src/worldcup_agent/api backend/.env.example backend/docs/LLM_AGENT.md backend/tests/integration/test_llm_fallback.py
git commit -m "feat: run production agent with llm fallback"
```

## Real Agent Completion Gate

- product API does not call `build_demo_registry()`;
- no-key mode completes a real 104-match forecast;
- enabled provider uses an explicit fixed model ID;
- every provider response is Pydantic-validated;
- one invalid JSON repair attempt is observable;
- Tool Registry is the only path from Agent to domain services;
- published numeric claims have 100% Evidence coverage;
- no schema or persisted event contains hidden chain-of-thought fields;
- replay performs zero LLM, network, prediction, or simulation calls;
- timeout recovery preserves completed batches and random seeds;
- provider failures emit a guardrail and use deterministic planning.
