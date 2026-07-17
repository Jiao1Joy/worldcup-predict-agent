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
