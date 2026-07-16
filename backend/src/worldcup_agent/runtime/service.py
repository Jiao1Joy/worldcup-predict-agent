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
