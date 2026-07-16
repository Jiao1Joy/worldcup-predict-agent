from __future__ import annotations


_FALLBACK_PLANS: dict[str, list[str]] = {
    "predict_tournament": [
        "inspect_snapshot",
        "ensure_artifacts",
        "predict_matches",
        "simulate_tournament",
        "critique",
        "explain",
        "publish",
    ],
    "predict_match": [
        "inspect_snapshot",
        "ensure_artifacts",
        "predict_matches",
        "critique",
        "explain",
        "publish",
    ],
    "inspect_backtest": [
        "inspect_snapshot",
        "load_backtest",
        "explain",
        "publish",
    ],
}


def fallback_plan(intent: str):
    # Local import to avoid a circular dependency with agent.planner.
    from worldcup_agent.agent.planner import ExecutionPlan

    steps = _FALLBACK_PLANS.get(intent)
    if steps is None:
        raise ValueError(f"no fallback plan for intent: {intent}")
    return ExecutionPlan(steps=steps, reason="deterministic fallback (no LLM provider)", prompt_version=None)
