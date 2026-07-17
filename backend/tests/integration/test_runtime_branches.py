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
