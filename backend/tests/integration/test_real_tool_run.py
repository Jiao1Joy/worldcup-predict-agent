from worldcup_agent.tools.contracts import ToolContext
from worldcup_agent.tools.production import ProductionServices, build_production_registry


async def test_production_registry_runs_real_forecast_services() -> None:
    services = ProductionServices.fixture()
    registry = build_production_registry(services)
    context = ToolContext(run_id="run-1", step_id="simulate")

    snapshot = await registry.execute("inspect_snapshot", {}, context)
    forecast = await registry.execute(
        "simulate_tournament",
        {"runs": 200, "seed": 7},
        context,
    )

    assert snapshot.output["data_version"] == services.data_version
    assert forecast.output["forecast_id"]
    assert len(forecast.output["matches"]) == 104
    assert forecast.output["provider"] != "demo-simulator"
