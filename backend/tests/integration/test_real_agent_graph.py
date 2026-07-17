from worldcup_agent.runtime.service import AgentRuntimeService


async def test_real_run_publishes_forecast_and_trace(runtime_store, production_registry, fallback_planner) -> None:
    service = AgentRuntimeService(runtime_store, production_registry, planner=fallback_planner, production=True)
    run = await service.create_run({"task": "预测世界杯冠军", "mode": "portfolio_frozen"})
    completed = await service.run(run.run_id)
    events = await runtime_store.list_events(run.run_id)

    assert completed.status.value == "completed"
    assert completed.tournament_state.get("matches_count", 0) == 104 or len(completed.tournament_state.get("matches", [])) == 104
    assert completed.evidence_refs
    assert {event.step_id for event in events} >= {"inspect_snapshot", "simulate_tournament", "critique", "explain", "publish"}
