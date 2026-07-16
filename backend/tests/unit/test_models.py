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


def test_package_exposes_version() -> None:
    import worldcup_agent

    assert worldcup_agent.__version__ == "0.1.0"


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
