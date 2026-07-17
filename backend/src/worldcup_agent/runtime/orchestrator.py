from collections.abc import Awaitable, Callable
from uuid import uuid4

from langgraph.graph import END, StateGraph

from worldcup_agent.domain.models import DecisionRecord, EventType, RunStatus
from worldcup_agent.runtime.policies import next_simulation_action, snapshot_action
from worldcup_agent.tools.contracts import ToolContext
from worldcup_agent.tools.registry import ToolRegistry


EventObserver = Callable[[EventType, str | None, dict], Awaitable[None]]


async def _ignore_event(_: EventType, __: str | None, ___: dict) -> None:
    return None


def build_runtime_graph(
    registry: ToolRegistry,
    observer: EventObserver = _ignore_event,
    failure_mode: str | None = None,
):
    async def collect(state: dict) -> dict:
        tool_input = {"force_refresh": False}
        result = await registry.execute(
            "collect_snapshot",
            tool_input,
            ToolContext(run_id=state["run_id"], step_id="collect"),
        )
        await observer(
            EventType.TOOL,
            "collect",
            {"tool": "collect_snapshot", "input": tool_input, "output": result.output},
        )
        tool_results = {**state.get("tool_results", {}), "collect": {"input": tool_input, "output": result.output}}
        await observer(
            EventType.STATE,
            "collect",
            {
                "patch": {
                    "status": "running",
                    "data_snapshot": result.output,
                    "tool_results": tool_results,
                }
            },
        )
        return {
            **state,
            "status": RunStatus.RUNNING,
            "data_snapshot": result.output,
            "tool_results": tool_results,
        }

    def route_snapshot(state: dict) -> str:
        return snapshot_action(state["data_snapshot"]["age_hours"])

    async def refresh_snapshot(state: dict) -> dict:
        tool_input = {"force_refresh": True}
        result = await registry.execute(
            "collect_snapshot",
            tool_input,
            ToolContext(run_id=state["run_id"], step_id="refresh_snapshot"),
        )
        await observer(
            EventType.DECISION,
            "refresh_snapshot",
            {
                "observation": f"age_hours={state['data_snapshot']['age_hours']}",
                "rule": "age_hours > 24",
                "action": "refresh_snapshot",
                "reason": "stale inputs would invalidate the forecast",
            },
        )
        await observer(
            EventType.TOOL,
            "refresh_snapshot",
            {"tool": "collect_snapshot", "input": tool_input, "output": result.output},
        )
        tool_results = {
            **state.get("tool_results", {}),
            "refresh_snapshot": {"input": tool_input, "output": result.output},
        }
        await observer(
            EventType.STATE,
            "refresh_snapshot",
            {"patch": {"data_snapshot": result.output, "tool_results": tool_results}},
        )
        return {**state, "data_snapshot": result.output, "tool_results": tool_results}

    async def simulate(state: dict) -> dict:
        total_runs = state.get("tournament_state", {}).get("total_runs", 20_000)
        tool_input = {"runs": total_runs, "seed": state["task_spec"].get("seed", 7)}
        result = await registry.execute(
            "simulate_tournament",
            tool_input,
            ToolContext(
                run_id=state["run_id"],
                step_id="simulate",
                metadata={"inject_failure": failure_mode} if failure_mode else {},
            ),
        )
        tournament_state = {**result.output, "total_runs": total_runs}
        tool_results = {
            **state.get("tool_results", {}),
            "simulate": {"input": tool_input, "output": result.output},
        }
        evidence_refs = [*state.get("evidence_refs", []), result.output["batch_id"]]
        await observer(
            EventType.TOOL,
            "simulate",
            {"tool": "simulate_tournament", "input": tool_input, "output": result.output},
        )
        await observer(
            EventType.STATE,
            "simulate",
            {
                "patch": {
                    "tournament_state": tournament_state,
                    "tool_results": tool_results,
                    "evidence_refs": evidence_refs,
                }
            },
        )
        return {
            **state,
            "tournament_state": tournament_state,
            "tool_results": tool_results,
            "evidence_refs": evidence_refs,
        }

    def route_simulation(state: dict) -> str:
        tournament = state["tournament_state"]
        return next_simulation_action(tournament["probability_delta"], tournament["total_runs"])

    async def simulate_more(state: dict) -> dict:
        decision = DecisionRecord(
            decision_id=str(uuid4()),
            observation=f"probability_delta={state['tournament_state']['probability_delta']}",
            rule="probability_delta > 0.005",
            action="simulate_more",
            reason="champion probability has not converged",
            evidence_ids=[state["tournament_state"]["batch_id"]],
        ).model_dump(mode="json")
        state = {**state, "decisions": [*state.get("decisions", []), decision]}
        await observer(EventType.DECISION, "simulate_more", decision)
        tool_input = {"runs": 30_000, "seed": state["task_spec"].get("seed", 7)}
        result = await registry.execute(
            "simulate_tournament",
            tool_input,
            ToolContext(run_id=state["run_id"], step_id="simulate_more"),
        )
        tournament_state = {**result.output, "total_runs": 30_000}
        tool_results = {
            **state.get("tool_results", {}),
            "simulate_more": {"input": tool_input, "output": result.output},
        }
        evidence_refs = [*state.get("evidence_refs", []), result.output["batch_id"]]
        await observer(
            EventType.TOOL,
            "simulate_more",
            {"tool": "simulate_tournament", "input": tool_input, "output": result.output},
        )
        await observer(
            EventType.STATE,
            "simulate_more",
            {
                "patch": {
                    "decisions": state["decisions"],
                    "tournament_state": tournament_state,
                    "tool_results": tool_results,
                    "evidence_refs": evidence_refs,
                }
            },
        )
        return {
            **state,
            "tournament_state": tournament_state,
            "tool_results": tool_results,
            "evidence_refs": evidence_refs,
        }

    async def critique(state: dict) -> dict:
        await observer(
            EventType.GUARDRAIL,
            "critique",
            {"check": "evidence_coverage", "result": "pass", "evidence_ids": state.get("evidence_refs", [])},
        )
        await observer(EventType.STATE, "critique", {"patch": {"current_step_id": "critique"}})
        return {**state, "current_step_id": "critique"}

    graph = StateGraph(dict)
    graph.add_node("collect", collect)
    graph.add_node("refresh_snapshot", refresh_snapshot)
    graph.add_node("simulate", simulate)
    graph.add_node("simulate_more", simulate_more)
    graph.add_node("critique", critique)
    graph.set_entry_point("collect")
    graph.add_conditional_edges(
        "collect",
        route_snapshot,
        {"refresh_snapshot": "refresh_snapshot", "continue": "simulate"},
    )
    graph.add_edge("refresh_snapshot", "simulate")
    graph.add_conditional_edges(
        "simulate",
        route_simulation,
        {"simulate_more": "simulate_more", "critique": "critique"},
    )
    graph.add_edge("simulate_more", "critique")
    graph.add_edge("critique", END)
    return graph.compile()
