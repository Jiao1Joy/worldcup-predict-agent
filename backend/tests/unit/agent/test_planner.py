from worldcup_agent.agent.planner import AgentPlanner, TaskSpec


async def test_parser_returns_typed_task(fake_provider) -> None:
    planner = AgentPlanner(fake_provider)
    spec = await planner.parse("预测冻结赛前快照的世界杯冠军")
    assert spec.intent == "predict_tournament"
    assert spec.mode == "portfolio_frozen"


async def test_fallback_plan_is_complete_without_provider() -> None:
    planner = AgentPlanner(provider=None)
    plan = await planner.plan(TaskSpec(intent="predict_tournament", mode="portfolio_frozen"))
    assert plan.steps == [
        "inspect_snapshot", "ensure_artifacts", "predict_matches",
        "simulate_tournament", "critique", "explain", "publish",
    ]
