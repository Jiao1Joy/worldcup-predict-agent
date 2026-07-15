# Agent Runtime Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a testable Agent runtime that plans tool calls, records state transitions and evidence, supports conditional branches, checkpoint recovery, human approval, replay, and a FastAPI/SSE interface.

**Architecture:** A LangGraph orchestrator operates on an explicit Pydantic `RunState`. Deterministic tools execute through a contract-enforcing registry; every decision, tool call, state patch, checkpoint, and evidence item is appended to SQLite as a `RunEvent`. FastAPI exposes run creation, snapshots, event streaming, replay, failure injection, and approval endpoints.

**Tech Stack:** Python 3.11, FastAPI, Pydantic 2, LangGraph, aiosqlite, pytest, pytest-asyncio, httpx

---

## File Structure

```text
backend/
├── pyproject.toml
├── src/worldcup_agent/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── app.py                 # FastAPI application and lifecycle
│   │   ├── dependencies.py        # Runtime/store dependency providers
│   │   ├── schemas.py             # HTTP request/response schemas
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── runs.py            # Run, SSE, replay, failure, approval routes
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── models.py              # RunState, events, decisions, evidence
│   │   └── errors.py              # Typed runtime and tool failures
│   ├── runtime/
│   │   ├── __init__.py
│   │   ├── orchestrator.py        # LangGraph definition and conditional routing
│   │   ├── policies.py            # Branch, retry, fallback, approval policies
│   │   ├── reducer.py             # Validated state patches and state diffs
│   │   ├── replay.py              # Rebuild state from append-only events
│   │   └── service.py             # Public run lifecycle service
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── contracts.py           # ToolSpec, ToolContext, ToolResult protocols
│   │   ├── registry.py            # Schema, timeout, retry, fallback enforcement
│   │   └── demo.py                # Deterministic portfolio tool adapters
│   ├── evidence/
│   │   ├── __init__.py
│   │   ├── critic.py              # Structured verdict generation
│   │   └── validator.py           # Evidence coverage and value validation
│   └── storage/
│       ├── __init__.py
│       ├── schema.sql              # SQLite schema
│       └── sqlite.py               # Event/checkpoint/evidence persistence
└── tests/
    ├── conftest.py
    ├── unit/
    │   ├── test_models.py
    │   ├── test_registry.py
    │   ├── test_reducer.py
    │   ├── test_policies.py
    │   └── test_evidence.py
    ├── integration/
    │   ├── test_runtime_branches.py
    │   ├── test_checkpoint_recovery.py
    │   ├── test_replay.py
    │   └── test_api_runs.py
    └── fixtures/
        └── completed_run.json
```

## Task 1: Bootstrap the Python Package

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/src/worldcup_agent/__init__.py`
- Create: `backend/tests/conftest.py`
- Test: `backend/tests/unit/test_models.py`

- [ ] **Step 1: Write the failing package import test**

```python
# backend/tests/unit/test_models.py
def test_package_exposes_version() -> None:
    import worldcup_agent

    assert worldcup_agent.__version__ == "0.1.0"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && python -m pytest tests/unit/test_models.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'worldcup_agent'`.

- [ ] **Step 3: Add package metadata and the minimal module**

```toml
# backend/pyproject.toml
[build-system]
requires = ["setuptools>=75", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "worldcup-agent"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "aiosqlite>=0.20,<1",
  "fastapi>=0.115,<1",
  "langgraph>=0.2,<1",
  "pydantic>=2.10,<3",
  "uvicorn[standard]>=0.34,<1",
]

[project.optional-dependencies]
dev = [
  "httpx>=0.28,<1",
  "pytest>=8.3,<9",
  "pytest-asyncio>=0.25,<1",
  "ruff>=0.9,<1",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py311"
```

```python
# backend/src/worldcup_agent/__init__.py
__version__ = "0.1.0"
```

```python
# backend/tests/conftest.py
from pathlib import Path

import pytest


@pytest.fixture
def sqlite_path(tmp_path: Path) -> Path:
    return tmp_path / "agent-test.sqlite3"
```

- [ ] **Step 4: Install the editable package and run the test**

Run: `cd backend && python -m pip install -e ".[dev]" && python -m pytest tests/unit/test_models.py -v`

Expected: PASS, `1 passed`.

- [ ] **Step 5: Commit the scaffold**

```bash
git add backend/pyproject.toml backend/src/worldcup_agent/__init__.py backend/tests
git commit -m "build: scaffold agent runtime package"
```

## Task 2: Define the Runtime Domain Models

**Files:**
- Create: `backend/src/worldcup_agent/domain/__init__.py`
- Create: `backend/src/worldcup_agent/domain/models.py`
- Create: `backend/src/worldcup_agent/domain/errors.py`
- Modify: `backend/tests/unit/test_models.py`

- [ ] **Step 1: Write failing model validation tests**

```python
# append to backend/tests/unit/test_models.py
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from worldcup_agent.domain.models import (
    DecisionRecord,
    EventType,
    RunEvent,
    RunState,
    RunStatus,
)


def test_run_state_starts_pending_with_empty_collections() -> None:
    state = RunState(run_id="run-1", task_spec={"intent": "predict_tournament"})

    assert state.status is RunStatus.PENDING
    assert state.tool_results == {}
    assert state.evidence_refs == []
    assert state.event_sequence == 0


def test_event_requires_non_negative_sequence() -> None:
    with pytest.raises(ValidationError):
        RunEvent(
            run_id="run-1",
            sequence=-1,
            event_type=EventType.PLAN,
            created_at=datetime.now(UTC),
            payload={},
        )


def test_decision_requires_observation_rule_and_action() -> None:
    decision = DecisionRecord(
        decision_id="dec-1",
        observation="probability_delta=0.018",
        rule="probability_delta > 0.005",
        action="simulate_more",
        reason="champion probability has not converged",
        evidence_ids=["SIM-029"],
    )

    assert decision.action == "simulate_more"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/test_models.py -v`

Expected: FAIL because `worldcup_agent.domain.models` does not exist.

- [ ] **Step 3: Implement enums, records, evidence, checkpoint, and state**

```python
# backend/src/worldcup_agent/domain/models.py
from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_HUMAN = "waiting_for_human"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    FAILED = "failed"


class StepStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class EventType(StrEnum):
    PLAN = "plan"
    TOOL = "tool"
    STATE = "state"
    DECISION = "decision"
    GUARDRAIL = "guardrail"
    CHECKPOINT = "checkpoint"
    RETRY = "retry"
    HUMAN = "human"
    COMPLETE = "complete"


class DecisionRecord(BaseModel):
    decision_id: str
    observation: str
    rule: str
    action: str
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    evidence_id: str
    kind: str
    value: Any
    source: str
    version: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RunEvent(BaseModel):
    run_id: str
    sequence: int = Field(ge=0)
    event_type: EventType
    step_id: str | None = None
    tool_call_id: str | None = None
    parent_step_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = Field(default_factory=dict)


class Checkpoint(BaseModel):
    checkpoint_id: str
    run_id: str
    sequence: int = Field(ge=0)
    state_hash: str
    state: dict[str, Any]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RunState(BaseModel):
    run_id: str
    task_spec: dict[str, Any]
    status: RunStatus = RunStatus.PENDING
    current_step_id: str | None = None
    step_statuses: dict[str, StepStatus] = Field(default_factory=dict)
    data_snapshot: dict[str, Any] = Field(default_factory=dict)
    model_snapshot: dict[str, Any] = Field(default_factory=dict)
    tournament_state: dict[str, Any] = Field(default_factory=dict)
    tool_results: dict[str, Any] = Field(default_factory=dict)
    decisions: list[DecisionRecord] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    checkpoint_id: str | None = None
    event_sequence: int = Field(default=0, ge=0)
```

```python
# backend/src/worldcup_agent/domain/errors.py
class AgentRuntimeError(Exception):
    retryable = False


class ToolTimeoutError(AgentRuntimeError):
    retryable = True


class ToolValidationError(AgentRuntimeError):
    retryable = False


class EvidenceValidationError(AgentRuntimeError):
    retryable = False


class HumanApprovalRequired(AgentRuntimeError):
    retryable = False
```

- [ ] **Step 4: Run model tests and static checks**

Run: `cd backend && python -m pytest tests/unit/test_models.py -v && python -m ruff check src tests`

Expected: all model tests PASS and Ruff reports no errors.

- [ ] **Step 5: Commit the domain model**

```bash
git add backend/src/worldcup_agent/domain backend/tests/unit/test_models.py
git commit -m "feat: define agent runtime domain models"
```

## Task 3: Implement Validated State Patches and Diffs

**Files:**
- Create: `backend/src/worldcup_agent/runtime/__init__.py`
- Create: `backend/src/worldcup_agent/runtime/reducer.py`
- Test: `backend/tests/unit/test_reducer.py`

- [ ] **Step 1: Write failing reducer tests**

```python
# backend/tests/unit/test_reducer.py
import pytest

from worldcup_agent.domain.models import RunState, RunStatus
from worldcup_agent.domain.errors import AgentRuntimeError
from worldcup_agent.runtime.reducer import apply_state_patch


def test_apply_state_patch_returns_before_after_diff() -> None:
    state = RunState(run_id="run-1", task_spec={})

    updated, diff = apply_state_patch(state, {"status": RunStatus.RUNNING})

    assert updated.status is RunStatus.RUNNING
    assert diff == {"status": {"before": "pending", "after": "running"}}


def test_apply_state_patch_rejects_unknown_fields() -> None:
    state = RunState(run_id="run-1", task_spec={})

    with pytest.raises(AgentRuntimeError, match="unknown state field"):
        apply_state_patch(state, {"secret_internal_value": 1})
```

- [ ] **Step 2: Run the reducer tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/test_reducer.py -v`

Expected: FAIL because `apply_state_patch` is not defined.

- [ ] **Step 3: Implement immutable validated patching**

```python
# backend/src/worldcup_agent/runtime/reducer.py
from typing import Any

from worldcup_agent.domain.errors import AgentRuntimeError
from worldcup_agent.domain.models import RunState


def _json_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def apply_state_patch(
    state: RunState,
    patch: dict[str, Any],
) -> tuple[RunState, dict[str, dict[str, Any]]]:
    unknown = set(patch) - set(RunState.model_fields)
    if unknown:
        field = sorted(unknown)[0]
        raise AgentRuntimeError(f"unknown state field: {field}")

    before = state.model_dump(mode="json")
    updated = state.model_copy(update=patch)
    updated = RunState.model_validate(updated.model_dump())
    after = updated.model_dump(mode="json")
    diff = {
        field: {"before": _json_value(before.get(field)), "after": _json_value(after.get(field))}
        for field in patch
        if before.get(field) != after.get(field)
    }
    return updated, diff
```

- [ ] **Step 4: Run reducer tests**

Run: `cd backend && python -m pytest tests/unit/test_reducer.py -v`

Expected: PASS, `2 passed`.

- [ ] **Step 5: Commit the reducer**

```bash
git add backend/src/worldcup_agent/runtime backend/tests/unit/test_reducer.py
git commit -m "feat: add validated agent state reducer"
```

## Task 4: Build the Tool Contract and Registry

**Files:**
- Create: `backend/src/worldcup_agent/tools/__init__.py`
- Create: `backend/src/worldcup_agent/tools/contracts.py`
- Create: `backend/src/worldcup_agent/tools/registry.py`
- Test: `backend/tests/unit/test_registry.py`

- [ ] **Step 1: Write failing timeout, retry, and schema tests**

```python
# backend/tests/unit/test_registry.py
import asyncio

import pytest
from pydantic import BaseModel

from worldcup_agent.domain.errors import ToolTimeoutError, ToolValidationError
from worldcup_agent.tools.contracts import ToolContext, ToolSpec
from worldcup_agent.tools.registry import ToolRegistry


class EchoInput(BaseModel):
    value: int


class EchoOutput(BaseModel):
    doubled: int


@pytest.mark.asyncio
async def test_registry_validates_and_executes_tool() -> None:
    registry = ToolRegistry()

    async def echo(payload: EchoInput, _: ToolContext) -> EchoOutput:
        return EchoOutput(doubled=payload.value * 2)

    registry.register(ToolSpec(name="echo", input_model=EchoInput, output_model=EchoOutput), echo)
    result = await registry.execute("echo", {"value": 4}, ToolContext(run_id="r", step_id="s"))

    assert result.output == {"doubled": 8}
    assert result.attempts == 1


@pytest.mark.asyncio
async def test_registry_rejects_invalid_input() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(name="echo", input_model=EchoInput, output_model=EchoOutput),
        lambda payload, context: EchoOutput(doubled=payload.value * 2),
    )

    with pytest.raises(ToolValidationError):
        await registry.execute("echo", {"value": "bad"}, ToolContext(run_id="r", step_id="s"))


@pytest.mark.asyncio
async def test_registry_retries_timeout() -> None:
    registry = ToolRegistry()

    async def slow(payload: EchoInput, _: ToolContext) -> EchoOutput:
        await asyncio.sleep(0.02)
        return EchoOutput(doubled=payload.value * 2)

    registry.register(
        ToolSpec(
            name="slow",
            input_model=EchoInput,
            output_model=EchoOutput,
            timeout_seconds=0.001,
            max_attempts=2,
        ),
        slow,
    )

    with pytest.raises(ToolTimeoutError):
        await registry.execute("slow", {"value": 2}, ToolContext(run_id="r", step_id="s"))
```

- [ ] **Step 2: Run the registry tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/test_registry.py -v`

Expected: FAIL because the tool contract modules do not exist.

- [ ] **Step 3: Implement tool contracts**

```python
# backend/src/worldcup_agent/tools/contracts.py
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field


class ToolContext(BaseModel):
    run_id: str
    step_id: str
    checkpoint_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolSpec(BaseModel):
    name: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    timeout_seconds: float = Field(default=30, gt=0)
    max_attempts: int = Field(default=3, ge=1)
    fallback: str | None = None
    idempotent: bool = True
    side_effect: str = "none"

    model_config = {"arbitrary_types_allowed": True}


class ToolExecutionResult(BaseModel):
    output: dict[str, Any]
    attempts: int
    latency_ms: int


ToolHandler = Callable[[BaseModel, ToolContext], Awaitable[BaseModel] | BaseModel]
```

- [ ] **Step 4: Implement the contract-enforcing registry**

```python
# backend/src/worldcup_agent/tools/registry.py
import asyncio
import inspect
from time import perf_counter

from pydantic import ValidationError

from worldcup_agent.domain.errors import ToolTimeoutError, ToolValidationError
from worldcup_agent.tools.contracts import (
    ToolContext,
    ToolExecutionResult,
    ToolHandler,
    ToolSpec,
)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, tuple[ToolSpec, ToolHandler]] = {}

    def register(self, spec: ToolSpec, handler: ToolHandler) -> None:
        if spec.name in self._tools:
            raise ValueError(f"tool already registered: {spec.name}")
        self._tools[spec.name] = (spec, handler)

    def get_spec(self, name: str) -> ToolSpec:
        try:
            return self._tools[name][0]
        except KeyError as exc:
            raise KeyError(f"unknown tool: {name}") from exc

    async def execute(
        self,
        name: str,
        raw_input: dict,
        context: ToolContext,
    ) -> ToolExecutionResult:
        spec, handler = self._tools[name]
        try:
            payload = spec.input_model.model_validate(raw_input)
        except ValidationError as exc:
            raise ToolValidationError(str(exc)) from exc

        started = perf_counter()
        for attempt in range(1, spec.max_attempts + 1):
            try:
                value = handler(payload, context)
                if inspect.isawaitable(value):
                    value = await asyncio.wait_for(value, timeout=spec.timeout_seconds)
                output = spec.output_model.model_validate(value).model_dump(mode="json")
                return ToolExecutionResult(
                    output=output,
                    attempts=attempt,
                    latency_ms=int((perf_counter() - started) * 1000),
                )
            except TimeoutError as exc:
                if attempt == spec.max_attempts:
                    raise ToolTimeoutError(f"tool {name} timed out after {attempt} attempts") from exc
        raise AssertionError("retry loop exited unexpectedly")
```

- [ ] **Step 5: Run the registry tests**

Run: `cd backend && python -m pytest tests/unit/test_registry.py -v`

Expected: PASS, `3 passed`.

- [ ] **Step 6: Commit the registry**

```bash
git add backend/src/worldcup_agent/tools backend/tests/unit/test_registry.py
git commit -m "feat: add contract enforcing tool registry"
```

## Task 5: Persist Events, Checkpoints, and Evidence in SQLite

**Files:**
- Create: `backend/src/worldcup_agent/storage/__init__.py`
- Create: `backend/src/worldcup_agent/storage/schema.sql`
- Create: `backend/src/worldcup_agent/storage/sqlite.py`
- Test: `backend/tests/integration/test_replay.py`

- [ ] **Step 1: Write the failing event persistence and replay test**

```python
# backend/tests/integration/test_replay.py
from worldcup_agent.domain.models import EvidenceItem, EventType, RunEvent, RunState
from worldcup_agent.runtime.replay import replay_run
from worldcup_agent.storage.sqlite import SQLiteRunStore


async def test_replay_rebuilds_state_from_state_events(sqlite_path) -> None:
    store = SQLiteRunStore(sqlite_path)
    await store.initialize()
    initial = RunState(run_id="run-1", task_spec={"intent": "predict"})
    await store.create_run(initial)
    await store.append_event(
        RunEvent(
            run_id="run-1",
            sequence=1,
            event_type=EventType.STATE,
            payload={"patch": {"status": "running"}},
        )
    )

    replayed = await replay_run(store, "run-1")

    assert replayed.status.value == "running"
    assert replayed.event_sequence == 1


async def test_evidence_store_round_trips_source_metadata(sqlite_path) -> None:
    store = SQLiteRunStore(sqlite_path)
    await store.initialize()
    await store.create_run(RunState(run_id="run-evidence", task_spec={}))
    evidence = EvidenceItem(
        evidence_id="SIM-20000-7",
        kind="simulation_batch",
        value={"Spain": 0.42},
        source="demo-simulator",
        version="seed-7",
    )

    await store.save_evidence("run-evidence", evidence)

    assert await store.list_evidence("run-evidence") == [evidence]
```

- [ ] **Step 2: Run the persistence test to verify it fails**

Run: `cd backend && python -m pytest tests/integration/test_replay.py -v`

Expected: FAIL because storage and replay modules do not exist.

- [ ] **Step 3: Create the SQLite schema**

```sql
-- backend/src/worldcup_agent/storage/schema.sql
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  initial_state_json TEXT NOT NULL,
  current_state_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
  run_id TEXT NOT NULL,
  sequence INTEGER NOT NULL,
  event_json TEXT NOT NULL,
  PRIMARY KEY (run_id, sequence),
  FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS checkpoints (
  checkpoint_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  sequence INTEGER NOT NULL,
  checkpoint_json TEXT NOT NULL,
  FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS evidence (
  evidence_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  evidence_json TEXT NOT NULL,
  FOREIGN KEY (run_id) REFERENCES runs(run_id)
);
```

- [ ] **Step 4: Implement the async store and replay reducer**

```python
# backend/src/worldcup_agent/storage/sqlite.py
from datetime import UTC, datetime
from pathlib import Path

import aiosqlite

from worldcup_agent.domain.models import Checkpoint, EvidenceItem, RunEvent, RunState


class SQLiteRunStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    async def initialize(self) -> None:
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(schema)
            await db.commit()

    async def create_run(self, state: RunState) -> None:
        now = datetime.now(UTC).isoformat()
        payload = state.model_dump_json()
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO runs VALUES (?, ?, ?, ?, ?)",
                (state.run_id, payload, payload, now, now),
            )
            await db.commit()

    async def append_event(self, event: RunEvent) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO events VALUES (?, ?, ?)",
                (event.run_id, event.sequence, event.model_dump_json()),
            )
            await db.commit()

    async def list_events(self, run_id: str, after: int = 0) -> list[RunEvent]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT event_json FROM events WHERE run_id=? AND sequence>? ORDER BY sequence",
                (run_id, after),
            )
            rows = await cursor.fetchall()
        return [RunEvent.model_validate_json(row[0]) for row in rows]

    async def get_initial_state(self, run_id: str) -> RunState:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT initial_state_json FROM runs WHERE run_id=?",
                (run_id,),
            )
            row = await cursor.fetchone()
        if row is None:
            raise KeyError(run_id)
        return RunState.model_validate_json(row[0])

    async def get_current_state(self, run_id: str) -> RunState:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT current_state_json FROM runs WHERE run_id=?",
                (run_id,),
            )
            row = await cursor.fetchone()
        if row is None:
            raise KeyError(run_id)
        return RunState.model_validate_json(row[0])

    async def save_evidence(self, run_id: str, evidence: EvidenceItem) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO evidence VALUES (?, ?, ?)",
                (evidence.evidence_id, run_id, evidence.model_dump_json()),
            )
            await db.commit()

    async def list_evidence(self, run_id: str) -> list[EvidenceItem]:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT evidence_json FROM evidence WHERE run_id=? ORDER BY evidence_id",
                (run_id,),
            )
            rows = await cursor.fetchall()
        return [EvidenceItem.model_validate_json(row[0]) for row in rows]
```

```python
# backend/src/worldcup_agent/runtime/replay.py
from worldcup_agent.domain.models import RunState
from worldcup_agent.runtime.reducer import apply_state_patch
from worldcup_agent.storage.sqlite import SQLiteRunStore


async def replay_run(store: SQLiteRunStore, run_id: str) -> RunState:
    state = await store.get_initial_state(run_id)
    for event in await store.list_events(run_id):
        if "patch" in event.payload:
            state, _ = apply_state_patch(state, event.payload["patch"])
        state = state.model_copy(update={"event_sequence": event.sequence})
    return state
```

- [ ] **Step 5: Run persistence and replay tests**

Run: `cd backend && python -m pytest tests/integration/test_replay.py -v`

Expected: PASS, `2 passed`.

- [ ] **Step 6: Commit storage and replay**

```bash
git add backend/src/worldcup_agent/storage backend/src/worldcup_agent/runtime/replay.py backend/tests/integration/test_replay.py
git commit -m "feat: persist and replay agent run events"
```

## Task 6: Add Deterministic Portfolio Tools

**Files:**
- Create: `backend/src/worldcup_agent/tools/demo.py`
- Test: `backend/tests/unit/test_registry.py`

- [ ] **Step 1: Write failing tests for deterministic tools and injected failure**

```python
# append to backend/tests/unit/test_registry.py
from worldcup_agent.tools.demo import build_demo_registry


@pytest.mark.asyncio
async def test_demo_simulator_is_reproducible() -> None:
    registry = build_demo_registry()
    context = ToolContext(run_id="r", step_id="simulate")

    first = await registry.execute("simulate_tournament", {"runs": 1000, "seed": 7}, context)
    second = await registry.execute("simulate_tournament", {"runs": 1000, "seed": 7}, context)

    assert first.output == second.output
    assert sum(first.output["champion_probabilities"].values()) == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_demo_simulator_can_inject_timeout() -> None:
    registry = build_demo_registry()
    context = ToolContext(
        run_id="r",
        step_id="simulate",
        metadata={"inject_failure": "timeout"},
    )

    with pytest.raises(ToolTimeoutError):
        await registry.execute("simulate_tournament", {"runs": 1000, "seed": 7}, context)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/test_registry.py -v`

Expected: FAIL because `build_demo_registry` does not exist.

- [ ] **Step 3: Implement snapshot, prediction, and simulation adapters**

```python
# backend/src/worldcup_agent/tools/demo.py
import asyncio
import random

from pydantic import BaseModel, Field

from worldcup_agent.tools.contracts import ToolContext, ToolSpec
from worldcup_agent.tools.registry import ToolRegistry


class SnapshotInput(BaseModel):
    force_refresh: bool = False


class SnapshotOutput(BaseModel):
    snapshot_id: str
    age_hours: float
    teams: int
    fixtures: int


class SimulateInput(BaseModel):
    runs: int = Field(ge=100, le=100_000)
    seed: int


class SimulateOutput(BaseModel):
    batch_id: str
    runs: int
    champion_probabilities: dict[str, float]
    probability_delta: float


async def collect_snapshot(payload: SnapshotInput, _: ToolContext) -> SnapshotOutput:
    return SnapshotOutput(
        snapshot_id="DATA-20260715",
        age_hours=0 if payload.force_refresh else 25,
        teams=48,
        fixtures=104,
    )


async def simulate_tournament(payload: SimulateInput, context: ToolContext) -> SimulateOutput:
    if context.metadata.get("inject_failure") == "timeout":
        await asyncio.sleep(0.02)
    rng = random.Random(payload.seed)
    raw = {"Spain": rng.random(), "Argentina": rng.random(), "France": rng.random()}
    total = sum(raw.values())
    probabilities = {team: value / total for team, value in raw.items()}
    return SimulateOutput(
        batch_id=f"SIM-{payload.runs}-{payload.seed}",
        runs=payload.runs,
        champion_probabilities=probabilities,
        probability_delta=0.018 if payload.runs < 30_000 else 0.004,
    )


def build_demo_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(name="collect_snapshot", input_model=SnapshotInput, output_model=SnapshotOutput),
        collect_snapshot,
    )
    registry.register(
        ToolSpec(
            name="simulate_tournament",
            input_model=SimulateInput,
            output_model=SimulateOutput,
            timeout_seconds=0.005,
            max_attempts=2,
        ),
        simulate_tournament,
    )
    return registry
```

- [ ] **Step 4: Run deterministic tool tests**

Run: `cd backend && python -m pytest tests/unit/test_registry.py -v`

Expected: all registry tests PASS.

- [ ] **Step 5: Commit the demo adapters**

```bash
git add backend/src/worldcup_agent/tools/demo.py backend/tests/unit/test_registry.py
git commit -m "feat: add deterministic prediction tool adapters"
```

## Task 7: Implement Policies and the LangGraph Orchestrator

**Files:**
- Create: `backend/src/worldcup_agent/runtime/policies.py`
- Create: `backend/src/worldcup_agent/runtime/orchestrator.py`
- Test: `backend/tests/unit/test_policies.py`
- Test: `backend/tests/integration/test_runtime_branches.py`

- [ ] **Step 1: Write failing policy tests**

```python
# backend/tests/unit/test_policies.py
from worldcup_agent.runtime.policies import next_simulation_action, snapshot_action


def test_stale_snapshot_requires_refresh() -> None:
    assert snapshot_action(age_hours=25) == "refresh_snapshot"
    assert snapshot_action(age_hours=2) == "continue"


def test_unconverged_simulation_adds_runs() -> None:
    assert next_simulation_action(probability_delta=0.018, total_runs=20_000) == "simulate_more"
    assert next_simulation_action(probability_delta=0.004, total_runs=30_000) == "critique"
```

- [ ] **Step 2: Run policy tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/test_policies.py -v`

Expected: FAIL because policy functions do not exist.

- [ ] **Step 3: Implement explicit branch policies**

```python
# backend/src/worldcup_agent/runtime/policies.py
def snapshot_action(age_hours: float) -> str:
    return "refresh_snapshot" if age_hours > 24 else "continue"


def next_simulation_action(probability_delta: float, total_runs: int) -> str:
    if probability_delta > 0.005 and total_runs < 50_000:
        return "simulate_more"
    return "critique"


def critic_action(model_disagreement: float, evidence_valid: bool) -> str:
    if not evidence_valid:
        return "repair_evidence"
    if model_disagreement > 0.06:
        return "run_critic"
    return "explain"
```

- [ ] **Step 4: Write the failing dynamic-branch integration test**

```python
# backend/tests/integration/test_runtime_branches.py
from worldcup_agent.domain.models import RunState
from worldcup_agent.runtime.orchestrator import build_runtime_graph
from worldcup_agent.tools.demo import build_demo_registry


async def test_runtime_refreshes_stale_data_and_adds_simulation_batch() -> None:
    graph = build_runtime_graph(build_demo_registry())
    initial = RunState(
        run_id="run-branch",
        task_spec={"intent": "predict_tournament", "seed": 7},
    )

    result = await graph.ainvoke(initial.model_dump(mode="json"))

    assert result["data_snapshot"]["age_hours"] == 0
    assert result["tournament_state"]["total_runs"] == 30_000
    assert any(item["action"] == "simulate_more" for item in result["decisions"])
```

- [ ] **Step 5: Implement the graph nodes and conditional edge**

```python
# backend/src/worldcup_agent/runtime/orchestrator.py
from collections.abc import Awaitable, Callable
from uuid import uuid4

from langgraph.graph import END, StateGraph

from worldcup_agent.domain.models import DecisionRecord, EventType, RunStatus
from worldcup_agent.runtime.policies import next_simulation_action, snapshot_action
from worldcup_agent.tools.contracts import ToolContext
from worldcup_agent.tools.registry import ToolRegistry


EventObserver = Callable[[EventType, str | None, dict], Awaitable[None]]


async def _ignore_event(_: EventType, __: str | None, ___: dict) -> None:
    return None


def build_runtime_graph(
    registry: ToolRegistry,
    observer: EventObserver = _ignore_event,
    failure_mode: str | None = None,
):
    async def collect(state: dict) -> dict:
        tool_input = {"force_refresh": False}
        result = await registry.execute(
            "collect_snapshot",
            tool_input,
            ToolContext(run_id=state["run_id"], step_id="collect"),
        )
        await observer(
            EventType.TOOL,
            "collect",
            {"tool": "collect_snapshot", "input": tool_input, "output": result.output},
        )
        tool_results = {**state.get("tool_results", {}), "collect": {"input": tool_input, "output": result.output}}
        await observer(
            EventType.STATE,
            "collect",
            {
                "patch": {
                    "status": "running",
                    "data_snapshot": result.output,
                    "tool_results": tool_results,
                }
            },
        )
        return {
            **state,
            "status": RunStatus.RUNNING,
            "data_snapshot": result.output,
            "tool_results": tool_results,
        }

    def route_snapshot(state: dict) -> str:
        return snapshot_action(state["data_snapshot"]["age_hours"])

    async def refresh_snapshot(state: dict) -> dict:
        tool_input = {"force_refresh": True}
        result = await registry.execute(
            "collect_snapshot",
            tool_input,
            ToolContext(run_id=state["run_id"], step_id="refresh_snapshot"),
        )
        await observer(
            EventType.DECISION,
            "refresh_snapshot",
            {
                "observation": f"age_hours={state['data_snapshot']['age_hours']}",
                "rule": "age_hours > 24",
                "action": "refresh_snapshot",
                "reason": "stale inputs would invalidate the forecast",
            },
        )
        await observer(
            EventType.TOOL,
            "refresh_snapshot",
            {"tool": "collect_snapshot", "input": tool_input, "output": result.output},
        )
        tool_results = {
            **state.get("tool_results", {}),
            "refresh_snapshot": {"input": tool_input, "output": result.output},
        }
        await observer(
            EventType.STATE,
            "refresh_snapshot",
            {"patch": {"data_snapshot": result.output, "tool_results": tool_results}},
        )
        return {**state, "data_snapshot": result.output, "tool_results": tool_results}

    async def simulate(state: dict) -> dict:
        total_runs = state.get("tournament_state", {}).get("total_runs", 20_000)
        tool_input = {"runs": total_runs, "seed": state["task_spec"].get("seed", 7)}
        result = await registry.execute(
            "simulate_tournament",
            tool_input,
            ToolContext(
                run_id=state["run_id"],
                step_id="simulate",
                metadata={"inject_failure": failure_mode} if failure_mode else {},
            ),
        )
        tournament_state = {**result.output, "total_runs": total_runs}
        tool_results = {
            **state.get("tool_results", {}),
            "simulate": {"input": tool_input, "output": result.output},
        }
        evidence_refs = [*state.get("evidence_refs", []), result.output["batch_id"]]
        await observer(
            EventType.TOOL,
            "simulate",
            {"tool": "simulate_tournament", "input": tool_input, "output": result.output},
        )
        await observer(
            EventType.STATE,
            "simulate",
            {
                "patch": {
                    "tournament_state": tournament_state,
                    "tool_results": tool_results,
                    "evidence_refs": evidence_refs,
                }
            },
        )
        return {
            **state,
            "tournament_state": tournament_state,
            "tool_results": tool_results,
            "evidence_refs": evidence_refs,
        }

    def route_simulation(state: dict) -> str:
        tournament = state["tournament_state"]
        return next_simulation_action(tournament["probability_delta"], tournament["total_runs"])

    async def simulate_more(state: dict) -> dict:
        decision = DecisionRecord(
            decision_id=str(uuid4()),
            observation=f"probability_delta={state['tournament_state']['probability_delta']}",
            rule="probability_delta > 0.005",
            action="simulate_more",
            reason="champion probability has not converged",
            evidence_ids=[state["tournament_state"]["batch_id"]],
        ).model_dump(mode="json")
        state = {**state, "decisions": [*state.get("decisions", []), decision]}
        await observer(EventType.DECISION, "simulate_more", decision)
        tool_input = {"runs": 30_000, "seed": state["task_spec"].get("seed", 7)}
        result = await registry.execute(
            "simulate_tournament",
            tool_input,
            ToolContext(run_id=state["run_id"], step_id="simulate_more"),
        )
        tournament_state = {**result.output, "total_runs": 30_000}
        tool_results = {
            **state.get("tool_results", {}),
            "simulate_more": {"input": tool_input, "output": result.output},
        }
        evidence_refs = [*state.get("evidence_refs", []), result.output["batch_id"]]
        await observer(
            EventType.TOOL,
            "simulate_more",
            {"tool": "simulate_tournament", "input": tool_input, "output": result.output},
        )
        await observer(
            EventType.STATE,
            "simulate_more",
            {
                "patch": {
                    "decisions": state["decisions"],
                    "tournament_state": tournament_state,
                    "tool_results": tool_results,
                    "evidence_refs": evidence_refs,
                }
            },
        )
        return {
            **state,
            "tournament_state": tournament_state,
            "tool_results": tool_results,
            "evidence_refs": evidence_refs,
        }

    async def critique(state: dict) -> dict:
        await observer(
            EventType.GUARDRAIL,
            "critique",
            {"check": "evidence_coverage", "result": "pass", "evidence_ids": state.get("evidence_refs", [])},
        )
        await observer(EventType.STATE, "critique", {"patch": {"current_step_id": "critique"}})
        return {**state, "current_step_id": "critique"}

    graph = StateGraph(dict)
    graph.add_node("collect", collect)
    graph.add_node("refresh_snapshot", refresh_snapshot)
    graph.add_node("simulate", simulate)
    graph.add_node("simulate_more", simulate_more)
    graph.add_node("critique", critique)
    graph.set_entry_point("collect")
    graph.add_conditional_edges(
        "collect",
        route_snapshot,
        {"refresh_snapshot": "refresh_snapshot", "continue": "simulate"},
    )
    graph.add_edge("refresh_snapshot", "simulate")
    graph.add_conditional_edges(
        "simulate",
        route_simulation,
        {"simulate_more": "simulate_more", "critique": "critique"},
    )
    graph.add_edge("simulate_more", "critique")
    graph.add_edge("critique", END)
    return graph.compile()
```

- [ ] **Step 6: Run policy and branch tests**

Run: `cd backend && python -m pytest tests/unit/test_policies.py tests/integration/test_runtime_branches.py -v`

Expected: all tests PASS and the branch test records `simulate_more`.

- [ ] **Step 7: Commit policy and orchestration**

```bash
git add backend/src/worldcup_agent/runtime backend/tests/unit/test_policies.py backend/tests/integration/test_runtime_branches.py
git commit -m "feat: add conditional agent orchestration graph"
```

## Task 8: Add the Critic and Evidence Validator

**Files:**
- Create: `backend/src/worldcup_agent/evidence/__init__.py`
- Create: `backend/src/worldcup_agent/evidence/critic.py`
- Create: `backend/src/worldcup_agent/evidence/validator.py`
- Test: `backend/tests/unit/test_evidence.py`

- [ ] **Step 1: Write failing evidence coverage tests**

```python
# backend/tests/unit/test_evidence.py
import pytest

from worldcup_agent.domain.errors import EvidenceValidationError
from worldcup_agent.domain.models import EvidenceItem
from worldcup_agent.evidence.critic import critic_verdict
from worldcup_agent.evidence.validator import validate_claims


def test_claims_require_existing_matching_evidence() -> None:
    evidence = {
        "SIM-030": EvidenceItem(
            evidence_id="SIM-030",
            kind="champion_probability",
            value={"Spain": 0.173},
            source="TournamentSimulator",
            version="3.1",
        )
    }
    validate_claims(
        [{"text": "Spain champion probability", "value": 0.173, "evidence_id": "SIM-030"}],
        evidence,
    )


def test_mismatched_evidence_value_is_rejected() -> None:
    evidence = {
        "SIM-030": EvidenceItem(
            evidence_id="SIM-030",
            kind="champion_probability",
            value={"Spain": 0.173},
            source="TournamentSimulator",
            version="3.1",
        )
    }
    with pytest.raises(EvidenceValidationError):
        validate_claims(
            [{"text": "Spain champion probability", "value": 0.20, "evidence_id": "SIM-030"}],
            evidence,
        )


def test_critic_requests_more_simulation_when_not_converged() -> None:
    verdict = critic_verdict(probability_delta=0.018, evidence_valid=True)
    assert verdict.recommended_action == "simulate_more"
```

- [ ] **Step 2: Run evidence tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/test_evidence.py -v`

Expected: FAIL because evidence modules do not exist.

- [ ] **Step 3: Implement deterministic critic and evidence validation**

```python
# backend/src/worldcup_agent/evidence/critic.py
from pydantic import BaseModel, Field


class CriticVerdict(BaseModel):
    passed: bool
    issues: list[str] = Field(default_factory=list)
    recommended_action: str
    params: dict = Field(default_factory=dict)


def critic_verdict(probability_delta: float, evidence_valid: bool) -> CriticVerdict:
    if not evidence_valid:
        return CriticVerdict(
            passed=False,
            issues=["evidence_invalid"],
            recommended_action="repair_evidence",
        )
    if probability_delta > 0.005:
        return CriticVerdict(
            passed=False,
            issues=["simulation_not_converged"],
            recommended_action="simulate_more",
            params={"additional_runs": 10_000},
        )
    return CriticVerdict(passed=True, recommended_action="explain")
```

```python
# backend/src/worldcup_agent/evidence/validator.py
from math import isclose

from worldcup_agent.domain.errors import EvidenceValidationError
from worldcup_agent.domain.models import EvidenceItem


def validate_claims(claims: list[dict], evidence: dict[str, EvidenceItem]) -> None:
    for claim in claims:
        evidence_id = claim["evidence_id"]
        if evidence_id not in evidence:
            raise EvidenceValidationError(f"missing evidence: {evidence_id}")
        values = evidence[evidence_id].value
        if not isinstance(values, dict):
            raise EvidenceValidationError(f"unsupported evidence value: {evidence_id}")
        matched = any(
            isinstance(value, (int, float)) and isclose(value, claim["value"], abs_tol=1e-9)
            for value in values.values()
        )
        if not matched:
            raise EvidenceValidationError(f"claim value mismatch: {evidence_id}")
```

- [ ] **Step 4: Run evidence tests**

Run: `cd backend && python -m pytest tests/unit/test_evidence.py -v`

Expected: PASS, `3 passed`.

- [ ] **Step 5: Commit evidence enforcement**

```bash
git add backend/src/worldcup_agent/evidence backend/tests/unit/test_evidence.py
git commit -m "feat: enforce evidence backed agent outputs"
```

## Task 9: Add Checkpoint Recovery and Human Approval

**Files:**
- Modify: `backend/src/worldcup_agent/storage/sqlite.py`
- Create: `backend/src/worldcup_agent/runtime/service.py`
- Test: `backend/tests/integration/test_checkpoint_recovery.py`

- [ ] **Step 1: Write failing checkpoint and approval tests**

```python
# backend/tests/integration/test_checkpoint_recovery.py
from worldcup_agent.domain.models import RunStatus
from worldcup_agent.runtime.service import AgentRuntimeService
from worldcup_agent.storage.sqlite import SQLiteRunStore
from worldcup_agent.tools.demo import build_demo_registry


async def test_timeout_recovers_from_checkpoint_without_losing_state(sqlite_path) -> None:
    store = SQLiteRunStore(sqlite_path)
    await store.initialize()
    service = AgentRuntimeService(store, build_demo_registry())
    run = await service.create_run({"intent": "predict_tournament", "seed": 7})

    recovered = await service.run(run.run_id, inject_failure="timeout-once")

    assert recovered.status is RunStatus.COMPLETED
    assert recovered.checkpoint_id is not None
    assert recovered.data_snapshot["snapshot_id"] == "DATA-20260715"
    assert any(error["retryable"] for error in recovered.errors)
    events = await store.list_events(run.run_id)
    assert [event.sequence for event in events] == list(range(1, len(events) + 1))
    assert any(event.event_type.value == "retry" for event in events)
    assert any(event.step_id == "simulate_more" for event in events)
    assert (await store.list_evidence(run.run_id))[0].evidence_id.startswith("SIM-")


async def test_conflicting_snapshot_pauses_for_human_and_resumes(sqlite_path) -> None:
    store = SQLiteRunStore(sqlite_path)
    await store.initialize()
    service = AgentRuntimeService(store, build_demo_registry())
    run = await service.create_run({"intent": "predict_tournament", "data_conflict": True})

    paused = await service.run(run.run_id)
    assert paused.status is RunStatus.WAITING_FOR_HUMAN

    resumed = await service.approve(run.run_id, choice="official", actor="portfolio-user")
    assert resumed.status is RunStatus.COMPLETED
    assert resumed.task_spec["approved_choice"] == "official"
    assert any(event.event_type.value == "human" for event in await store.list_events(run.run_id))
```

- [ ] **Step 2: Run recovery tests to verify they fail**

Run: `cd backend && python -m pytest tests/integration/test_checkpoint_recovery.py -v`

Expected: FAIL because `AgentRuntimeService` does not exist.

- [ ] **Step 3: Add checkpoint store methods**

```python
# add to backend/src/worldcup_agent/storage/sqlite.py
    async def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO checkpoints VALUES (?, ?, ?, ?)",
                (
                    checkpoint.checkpoint_id,
                    checkpoint.run_id,
                    checkpoint.sequence,
                    checkpoint.model_dump_json(),
                ),
            )
            await db.commit()

    async def latest_checkpoint(self, run_id: str) -> Checkpoint | None:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT checkpoint_json FROM checkpoints WHERE run_id=? ORDER BY sequence DESC LIMIT 1",
                (run_id,),
            )
            row = await cursor.fetchone()
        return Checkpoint.model_validate_json(row[0]) if row else None

    async def update_current_state(self, state: RunState) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE runs SET current_state_json=?, updated_at=? WHERE run_id=?",
                (state.model_dump_json(), datetime.now(UTC).isoformat(), state.run_id),
            )
            await db.commit()
```

- [ ] **Step 4: Implement the lifecycle service, event recorder, and one-shot failure injection**

```python
# backend/src/worldcup_agent/runtime/service.py
import hashlib
from uuid import uuid4

from worldcup_agent.domain.errors import ToolTimeoutError
from worldcup_agent.domain.models import (
    Checkpoint,
    EvidenceItem,
    EventType,
    RunEvent,
    RunState,
    RunStatus,
)
from worldcup_agent.runtime.orchestrator import build_runtime_graph
from worldcup_agent.storage.sqlite import SQLiteRunStore
from worldcup_agent.tools.registry import ToolRegistry


class EventRecorder:
    def __init__(self, store: SQLiteRunStore, run_id: str, sequence: int) -> None:
        self.store = store
        self.run_id = run_id
        self.sequence = sequence

    async def emit(self, event_type: EventType, step_id: str | None, payload: dict) -> None:
        self.sequence += 1
        await self.store.append_event(
            RunEvent(
                run_id=self.run_id,
                sequence=self.sequence,
                event_type=event_type,
                step_id=step_id,
                payload=payload,
            )
        )


class AgentRuntimeService:
    def __init__(self, store: SQLiteRunStore, registry: ToolRegistry) -> None:
        self.store = store
        self.registry = registry

    async def create_run(self, task_spec: dict) -> RunState:
        state = RunState(run_id=str(uuid4()), task_spec=task_spec)
        await self.store.create_run(state)
        recorder = EventRecorder(self.store, state.run_id, state.event_sequence)
        await recorder.emit(
            EventType.PLAN,
            None,
            {
                "stages": ["collect", "validate", "predict", "simulate", "critique", "explain"],
                "task_spec": task_spec,
            },
        )
        state = state.model_copy(update={"event_sequence": recorder.sequence})
        await self.store.update_current_state(state)
        return state

    async def run(self, run_id: str, inject_failure: str | None = None) -> RunState:
        state = await self.store.get_current_state(run_id)
        recorder = EventRecorder(self.store, run_id, state.event_sequence)
        if state.task_spec.get("data_conflict") and not state.task_spec.get("approved_choice"):
            await recorder.emit(
                EventType.HUMAN,
                "validate",
                {
                    "patch": {"status": "waiting_for_human"},
                    "reason": "official and cached data snapshots disagree",
                    "choices": ["official", "cached"],
                },
            )
            paused = state.model_copy(
                update={"status": RunStatus.WAITING_FOR_HUMAN, "event_sequence": recorder.sequence}
            )
            await self.store.update_current_state(paused)
            return paused

        checkpoint = self._checkpoint(state)
        await self.store.save_checkpoint(checkpoint)
        await recorder.emit(
            EventType.CHECKPOINT,
            state.current_step_id,
            {"patch": {"checkpoint_id": checkpoint.checkpoint_id}, "state_hash": checkpoint.state_hash},
        )
        state = state.model_copy(
            update={"checkpoint_id": checkpoint.checkpoint_id, "event_sequence": recorder.sequence}
        )
        if inject_failure == "timeout-once":
            try:
                return await self._execute(state, recorder, failure_mode="timeout")
            except ToolTimeoutError as exc:
                checkpoint_state = RunState.model_validate(checkpoint.state)
                errors = [
                    *checkpoint_state.errors,
                    {"error_type": "timeout", "message": str(exc), "retryable": True, "attempt": 1},
                ]
                recovery_patch = checkpoint_state.model_dump(mode="json")
                recovery_patch.update(
                    {
                        "status": "recovering",
                        "errors": errors,
                        "checkpoint_id": checkpoint.checkpoint_id,
                    }
                )
                recovery_patch.pop("event_sequence")
                await recorder.emit(
                    EventType.RETRY,
                    "simulate",
                    {
                        "patch": recovery_patch,
                        "backoff_ms": 0,
                        "restored_checkpoint_id": checkpoint.checkpoint_id,
                    },
                )
                restored = checkpoint_state.model_copy(
                    update={
                        "status": RunStatus.RECOVERING,
                        "errors": errors,
                        "checkpoint_id": checkpoint.checkpoint_id,
                        "event_sequence": recorder.sequence,
                    }
                )
                await self.store.update_current_state(restored)
                state = restored

        return await self._execute(state, recorder)

    async def approve(self, run_id: str, choice: str, actor: str) -> RunState:
        state = await self.store.get_current_state(run_id)
        task_spec = {**state.task_spec, "approved_choice": choice, "approved_by": actor}
        recorder = EventRecorder(self.store, run_id, state.event_sequence)
        await recorder.emit(
            EventType.HUMAN,
            "validate",
            {
                "patch": {"task_spec": task_spec, "status": "running"},
                "choice": choice,
                "actor": actor,
            },
        )
        resumed = state.model_copy(
            update={
                "task_spec": task_spec,
                "status": RunStatus.RUNNING,
                "event_sequence": recorder.sequence,
            }
        )
        await self.store.update_current_state(resumed)
        return await self._execute(resumed, recorder)

    async def _execute(
        self,
        state: RunState,
        recorder: EventRecorder,
        failure_mode: str | None = None,
    ) -> RunState:
        graph = build_runtime_graph(self.registry, recorder.emit, failure_mode)
        try:
            result = await graph.ainvoke(state.model_dump(mode="json"))
            tournament = result.get("tournament_state", {})
            if tournament.get("batch_id"):
                await self.store.save_evidence(
                    state.run_id,
                    EvidenceItem(
                        evidence_id=tournament["batch_id"],
                        kind="simulation_batch",
                        value=tournament["champion_probabilities"],
                        source="demo-simulator",
                        version=f"seed-{state.task_spec.get('seed', 7)}",
                    ),
                )
            await recorder.emit(
                EventType.COMPLETE,
                "explain",
                {
                    "patch": {
                        "status": "completed",
                        "current_step_id": "explain",
                        "checkpoint_id": state.checkpoint_id,
                    }
                },
            )
            completed = RunState.model_validate(result).model_copy(
                update={
                    "status": RunStatus.COMPLETED,
                    "current_step_id": "explain",
                    "checkpoint_id": state.checkpoint_id,
                    "event_sequence": recorder.sequence,
                }
            )
            await self.store.update_current_state(completed)
            return completed
        except Exception:
            checkpoint = await self.store.latest_checkpoint(state.run_id)
            if checkpoint is not None:
                restored = RunState.model_validate(checkpoint.state).model_copy(
                    update={"checkpoint_id": checkpoint.checkpoint_id, "event_sequence": recorder.sequence}
                )
                await self.store.update_current_state(restored)
            raise

    @staticmethod
    def _checkpoint(state: RunState) -> Checkpoint:
        state_json = state.model_dump_json()
        return Checkpoint(
            checkpoint_id=str(uuid4()),
            run_id=state.run_id,
            sequence=state.event_sequence,
            state_hash=hashlib.sha256(state_json.encode()).hexdigest(),
            state=state.model_dump(mode="json"),
        )
```

- [ ] **Step 5: Run recovery tests**

Run: `cd backend && python -m pytest tests/integration/test_checkpoint_recovery.py -v`

Expected: PASS, `2 passed`.

- [ ] **Step 6: Commit recovery and approval support**

```bash
git add backend/src/worldcup_agent/storage/sqlite.py backend/src/worldcup_agent/runtime/service.py backend/tests/integration/test_checkpoint_recovery.py
git commit -m "feat: add checkpoint recovery and human approval"
```

## Task 10: Expose Run, SSE, Replay, Failure, and Approval APIs

**Files:**
- Create: `backend/src/worldcup_agent/api/__init__.py`
- Create: `backend/src/worldcup_agent/api/app.py`
- Create: `backend/src/worldcup_agent/api/dependencies.py`
- Create: `backend/src/worldcup_agent/api/schemas.py`
- Create: `backend/src/worldcup_agent/api/routes/__init__.py`
- Create: `backend/src/worldcup_agent/api/routes/runs.py`
- Test: `backend/tests/integration/test_api_runs.py`

- [ ] **Step 1: Write failing API lifecycle tests**

```python
# backend/tests/integration/test_api_runs.py
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
```

- [ ] **Step 2: Run API tests to verify they fail**

Run: `cd backend && python -m pytest tests/integration/test_api_runs.py -v`

Expected: FAIL because `create_app` and routes do not exist.

- [ ] **Step 3: Define HTTP schemas and dependencies**

```python
# backend/src/worldcup_agent/api/schemas.py
from pydantic import BaseModel, Field


class CreateRunRequest(BaseModel):
    task: str = Field(min_length=1)
    seed: int = 7
    data_conflict: bool = False


class FailureRequest(BaseModel):
    failure: str


class ApprovalRequest(BaseModel):
    choice: str
    actor: str
```

```python
# backend/src/worldcup_agent/api/dependencies.py
from pathlib import Path

from worldcup_agent.runtime.service import AgentRuntimeService
from worldcup_agent.storage.sqlite import SQLiteRunStore
from worldcup_agent.tools.demo import build_demo_registry


async def build_service(path: str | Path) -> AgentRuntimeService:
    store = SQLiteRunStore(path)
    await store.initialize()
    return AgentRuntimeService(store, build_demo_registry())
```

- [ ] **Step 4: Implement run routes including SSE formatting**

```python
# backend/src/worldcup_agent/api/routes/runs.py
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from worldcup_agent.api.schemas import ApprovalRequest, CreateRunRequest, FailureRequest
from worldcup_agent.domain.models import RunEvent
from worldcup_agent.runtime.replay import replay_run
from worldcup_agent.runtime.service import AgentRuntimeService

router = APIRouter(prefix="/api/runs", tags=["runs"])


def format_sse(event: RunEvent) -> str:
    return (
        f"id: {event.sequence}\n"
        f"event: {event.event_type.value}\n"
        f"data: {event.model_dump_json()}\n\n"
    )


def get_service(request: Request) -> AgentRuntimeService:
    return request.app.state.runtime_service


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_run(payload: CreateRunRequest, service: AgentRuntimeService = Depends(get_service)):
    state = await service.create_run(
        {
            "intent": "predict_tournament",
            "task": payload.task,
            "seed": payload.seed,
            "data_conflict": payload.data_conflict,
        }
    )
    return state.model_dump(mode="json")


@router.get("/{run_id}")
async def get_run(run_id: str, service: AgentRuntimeService = Depends(get_service)):
    try:
        state = await replay_run(service.store, run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc
    return state.model_dump(mode="json")


@router.get("/{run_id}/initial")
async def get_initial_run(run_id: str, service: AgentRuntimeService = Depends(get_service)):
    try:
        state = await service.store.get_initial_state(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc
    return state.model_dump(mode="json")


@router.post("/{run_id}/start")
async def start_run(run_id: str, service: AgentRuntimeService = Depends(get_service)):
    state = await service.run(run_id)
    return state.model_dump(mode="json")


@router.post("/{run_id}/inject-failure")
async def inject_failure(
    run_id: str,
    payload: FailureRequest,
    service: AgentRuntimeService = Depends(get_service),
):
    state = await service.run(run_id, inject_failure=payload.failure)
    return state.model_dump(mode="json")


@router.post("/{run_id}/approve")
async def approve(
    run_id: str,
    payload: ApprovalRequest,
    service: AgentRuntimeService = Depends(get_service),
):
    state = await service.approve(run_id, payload.choice, payload.actor)
    return state.model_dump(mode="json")


@router.get("/{run_id}/events")
async def stream_events(run_id: str, request: Request, service: AgentRuntimeService = Depends(get_service)):
    async def event_source():
        after = int(request.headers.get("last-event-id", "0"))
        while not await request.is_disconnected():
            events = await service.store.list_events(run_id, after=after)
            for event in events:
                after = event.sequence
                yield format_sse(event)
            await asyncio.sleep(0.25)

    return StreamingResponse(event_source(), media_type="text/event-stream")
```

- [ ] **Step 5: Create the FastAPI factory**

```python
# backend/src/worldcup_agent/api/app.py
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from worldcup_agent.api.dependencies import build_service
from worldcup_agent.api.routes.runs import router as runs_router


def create_app(sqlite_path: str | Path = "agent.sqlite3") -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.runtime_service = await build_service(sqlite_path)
        yield

    app = FastAPI(title="World Cup Prediction Agent", lifespan=lifespan)
    app.include_router(runs_router)
    return app


app = create_app()
```

- [ ] **Step 6: Run API tests**

Run: `cd backend && python -m pytest tests/integration/test_api_runs.py -v`

Expected: PASS, `3 passed`.

- [ ] **Step 7: Run the entire backend suite**

Run: `cd backend && python -m pytest -q && python -m ruff check src tests`

Expected: all tests PASS and Ruff reports no errors.

- [ ] **Step 8: Commit the API**

```bash
git add backend/src/worldcup_agent/api backend/tests/integration/test_api_runs.py
git commit -m "feat: expose observable agent run api"
```

## Task 11: Add Complete-Run Fixture and Backend Demo Documentation

**Files:**
- Create: `backend/tests/fixtures/completed_run.json`
- Create: `backend/README.md`
- Modify: `README.md`

- [ ] **Step 1: Generate a completed run through the public service**

Run: `cd backend && python -m worldcup_agent.api.generate_fixture --output tests/fixtures/completed_run.json`

Expected before implementation: FAIL with `No module named worldcup_agent.api.generate_fixture`.

- [ ] **Step 2: Add the fixture generator**

```python
# backend/src/worldcup_agent/api/generate_fixture.py
import argparse
import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from worldcup_agent.api.dependencies import build_service


async def generate(output: Path) -> None:
    with TemporaryDirectory() as directory:
        service = await build_service(Path(directory) / "fixture.sqlite3")
        run = await service.create_run({"intent": "predict_tournament", "seed": 7})
        completed = await service.run(run.run_id)
        events = await service.store.list_events(run.run_id)
        output.write_text(
            json.dumps(
                {
                    "initial_state": run.model_copy(update={"event_sequence": 0}).model_dump(mode="json"),
                    "state": completed.model_dump(mode="json"),
                    "events": [event.model_dump(mode="json") for event in events],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(generate(args.output))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Generate and validate the fixture**

Run: `cd backend && python -m worldcup_agent.api.generate_fixture --output tests/fixtures/completed_run.json && python -m pytest -q`

Expected: fixture file is created and the complete test suite PASSes.

- [ ] **Step 4: Document local startup and demonstration endpoints**

````markdown
<!-- backend/README.md -->
# Agent Runtime

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
````

Update the repository `README.md` to link the design document, both implementation plans, and backend startup instructions.

- [ ] **Step 5: Run final backend verification**

Run: `cd backend && python -m pytest -q && python -m ruff check src tests`

Expected: all tests PASS and Ruff reports no errors.

- [ ] **Step 6: Commit the fixture and documentation**

```bash
git add README.md backend/README.md backend/src/worldcup_agent/api/generate_fixture.py backend/tests/fixtures/completed_run.json
git commit -m "docs: add agent runtime demo fixture"
```

## Backend Plan Completion Gate

Run all of the following before starting the frontend plan:

```bash
cd backend
python -m pytest -q
python -m ruff check src tests
python -m worldcup_agent.api.generate_fixture --output tests/fixtures/completed_run.json
```

Required evidence:

- all tests pass;
- Ruff reports no errors;
- `completed_run.json` contains a completed state and ordered events;
- stale-data and simulation-convergence branches appear in integration tests;
- timeout recovery preserves the snapshot and checkpoint ID;
- human approval pauses and resumes the run.
