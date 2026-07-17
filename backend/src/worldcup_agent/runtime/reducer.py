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
