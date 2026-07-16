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
