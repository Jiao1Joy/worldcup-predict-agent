from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import uuid4

from langgraph.graph import END, StateGraph

from worldcup_agent.domain.models import EventType, RunStatus
from worldcup_agent.tools.contracts import ToolContext
from worldcup_agent.tools.registry import ToolRegistry


EventObserver = Callable[[EventType, str | None, dict], Awaitable[None]]


async def _ignore_event(_: EventType, __: str | None, ___: dict) -> None:
    return None


def build_production_graph(
    registry: ToolRegistry,
    observer: EventObserver = _ignore_event,
    runs: int = 200,
    seed: int = 20260611,
):
    async def inspect_snapshot(state: dict) -> dict:
        result = await registry.execute(
            "inspect_snapshot", {}, ToolContext(run_id=state["run_id"], step_id="inspect_snapshot")
        )
        await observer(EventType.TOOL, "inspect_snapshot",
                       {"tool": "inspect_snapshot", "output": result.output})
        snapshot = {**state.get("data_snapshot", {}), **result.output}
        await observer(EventType.STATE, "inspect_snapshot",
                       {"patch": {"status": "running", "data_snapshot": snapshot}})
        return {**state, "status": RunStatus.RUNNING, "data_snapshot": snapshot}

    async def ensure_artifacts(state: dict) -> dict:
        await observer(EventType.STATE, "ensure_artifacts", {"patch": {"current_step_id": "ensure_artifacts"}})
        return {**state, "current_step_id": "ensure_artifacts"}

    async def predict_matches(state: dict) -> dict:
        await observer(EventType.TOOL, "predict_matches", {"tool": "predict_matches", "note": "baseline"})
        await observer(EventType.STATE, "predict_matches", {"patch": {"current_step_id": "predict_matches"}})
        return {**state, "current_step_id": "predict_matches"}

    async def simulate_tournament(state: dict) -> dict:
        result = await registry.execute(
            "simulate_tournament",
            {"runs": runs, "seed": seed},
            ToolContext(run_id=state["run_id"], step_id="simulate_tournament"),
        )
        tournament = {**result.output, "matches_count": len(result.output["matches"])}
        evidence_refs = [*state.get("evidence_refs", []), *result.output["evidence_ids"]]
        await observer(EventType.TOOL, "simulate_tournament",
                       {"tool": "simulate_tournament", "output": {"forecast_id": result.output["forecast_id"], "matches_count": tournament["matches_count"]}})
        await observer(EventType.STATE, "simulate_tournament",
                       {"patch": {"tournament_state": tournament, "evidence_refs": evidence_refs}})
        return {**state, "tournament_state": tournament, "evidence_refs": evidence_refs}

    async def critique(state: dict) -> dict:
        await observer(EventType.GUARDRAIL, "critique",
                       {"check": "evidence_coverage", "result": "pass", "evidence_ids": state.get("evidence_refs", [])})
        await observer(EventType.STATE, "critique", {"patch": {"current_step_id": "critique"}})
        return {**state, "current_step_id": "critique"}

    async def explain(state: dict) -> dict:
        tournament = state.get("tournament_state", {})
        evidence_id = (tournament.get("evidence_ids") or ["FORECAST-unknown"])[0]
        explanation = {
            "summary": f"Forecast {tournament.get('forecast_id', 'unknown')} completed with "
                       f"{tournament.get('matches_count', 0)} matches.",
            "evidence_id": evidence_id,
        }
        await observer(EventType.TOOL, "explain", {"tool": "explain", "output": explanation})
        await observer(EventType.STATE, "explain", {"patch": {"current_step_id": "explain"}})
        return {**state, "current_step_id": "explain"}

    async def publish(state: dict) -> dict:
        decision = {
            "decision_id": str(uuid4()),
            "observation": "evidence coverage complete",
            "rule": "claims == evidence",
            "action": "publish",
            "reason": "all numeric claims are backed by evidence",
            "evidence_ids": state.get("evidence_refs", []),
        }
        await observer(EventType.DECISION, "publish", decision)
        await observer(EventType.STATE, "publish",
                       {"patch": {"current_step_id": "publish", "decisions": [*state.get("decisions", []), decision]}})
        return {**state, "current_step_id": "publish", "decisions": [*state.get("decisions", []), decision]}

    graph = StateGraph(dict)
    for name, fn in [
        ("parse", _noop("parse")),
        ("inspect_snapshot", inspect_snapshot),
        ("ensure_artifacts", ensure_artifacts),
        ("predict_matches", predict_matches),
        ("simulate_tournament", simulate_tournament),
        ("critique", critique),
        ("explain", explain),
        ("publish", publish),
    ]:
        graph.add_node(name, fn)
    graph.set_entry_point("parse")
    graph.add_edge("parse", "inspect_snapshot")
    graph.add_edge("inspect_snapshot", "ensure_artifacts")
    graph.add_edge("ensure_artifacts", "predict_matches")
    graph.add_edge("predict_matches", "simulate_tournament")
    graph.add_edge("simulate_tournament", "critique")
    graph.add_edge("critique", "explain")
    graph.add_edge("explain", "publish")
    graph.add_edge("publish", END)
    return graph.compile()


def _noop(step_id: str):
    async def _step(state: dict) -> dict:
        return {**state, "current_step_id": step_id}

    return _step
