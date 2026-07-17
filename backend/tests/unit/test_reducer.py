import pytest

from worldcup_agent.domain.errors import AgentRuntimeError
from worldcup_agent.domain.models import RunState, RunStatus
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
