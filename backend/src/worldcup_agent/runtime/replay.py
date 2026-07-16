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
