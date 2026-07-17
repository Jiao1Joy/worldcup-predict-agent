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
