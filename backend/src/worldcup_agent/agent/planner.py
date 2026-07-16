from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from worldcup_agent.llm.contracts import LLMUnavailableError, StructuredRequest
from worldcup_agent.llm.fallback import fallback_plan
from worldcup_agent.llm.prompts import PLANNER_V1, TASK_PARSER_V1


class TaskSpec(BaseModel):
    intent: Literal["predict_match", "predict_tournament", "inspect_backtest"]
    mode: Literal["portfolio_frozen", "rebuild", "as_of"]
    as_of: str | None = None
    simulation_runs: int = Field(default=30_000, ge=100, le=100_000)
    explain_level: Literal["summary", "evidence"] = "evidence"
    allow_human_review: bool = True


class ExecutionPlan(BaseModel):
    steps: list[str]
    reason: str
    prompt_version: str | None = None


_ALLOWED_STEPS = {
    "inspect_snapshot", "ensure_artifacts", "predict_matches",
    "simulate_tournament", "load_backtest", "critique",
    "explain", "publish",
}


class AgentPlanner:
    def __init__(self, provider) -> None:
        self.provider = provider

    async def parse(self, task_text: str) -> TaskSpec:
        if self.provider is None:
            return self._fallback_parse(task_text)
        request = StructuredRequest(
            system_prompt=TASK_PARSER_V1,
            user_payload={"task": task_text},
            prompt_version="task-parser-v1",
        )
        try:
            response = await self.provider.complete_structured(request, TaskSpec)
            return response.value
        except LLMUnavailableError:
            return self._fallback_parse(task_text)

    async def plan(self, spec: TaskSpec) -> ExecutionPlan:
        if self.provider is None:
            return fallback_plan(spec.intent)
        request = StructuredRequest(
            system_prompt=PLANNER_V1,
            user_payload={"spec": spec.model_dump(), "allowlist": sorted(_ALLOWED_STEPS)},
            prompt_version="planner-v1",
        )
        try:
            response = await self.provider.complete_structured(request, ExecutionPlan)
            plan = response.value
            self._validate(plan)
            return plan
        except LLMUnavailableError:
            return fallback_plan(spec.intent)

    @staticmethod
    def _validate(plan: ExecutionPlan) -> None:
        for step in plan.steps:
            if step not in _ALLOWED_STEPS:
                raise ValueError(f"plan contains unauthorized step: {step}")

    @staticmethod
    def _fallback_parse(task_text: str) -> TaskSpec:
        text = task_text.casefold()
        if "backtest" in text or "回测" in text:
            intent = "inspect_backtest"
        elif "match" in text or "单场" in text:
            intent = "predict_match"
        else:
            intent = "predict_tournament"
        return TaskSpec(intent=intent, mode="portfolio_frozen")
