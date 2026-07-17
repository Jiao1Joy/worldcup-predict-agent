import asyncio
import random

from pydantic import BaseModel, Field

from worldcup_agent.tools.contracts import ToolContext, ToolSpec
from worldcup_agent.tools.registry import ToolRegistry


class SnapshotInput(BaseModel):
    force_refresh: bool = False


class SnapshotOutput(BaseModel):
    snapshot_id: str
    age_hours: float
    teams: int
    fixtures: int


class SimulateInput(BaseModel):
    runs: int = Field(ge=100, le=100_000)
    seed: int


class SimulateOutput(BaseModel):
    batch_id: str
    runs: int
    champion_probabilities: dict[str, float]
    probability_delta: float


async def collect_snapshot(payload: SnapshotInput, _: ToolContext) -> SnapshotOutput:
    return SnapshotOutput(
        snapshot_id="DATA-20260715",
        age_hours=0 if payload.force_refresh else 25,
        teams=48,
        fixtures=104,
    )


async def simulate_tournament(payload: SimulateInput, context: ToolContext) -> SimulateOutput:
    if context.metadata.get("inject_failure") == "timeout":
        await asyncio.sleep(0.02)
    rng = random.Random(payload.seed)
    raw = {"Spain": rng.random(), "Argentina": rng.random(), "France": rng.random()}
    total = sum(raw.values())
    probabilities = {team: value / total for team, value in raw.items()}
    return SimulateOutput(
        batch_id=f"SIM-{payload.runs}-{payload.seed}",
        runs=payload.runs,
        champion_probabilities=probabilities,
        probability_delta=0.018 if payload.runs < 30_000 else 0.004,
    )


def build_demo_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(name="collect_snapshot", input_model=SnapshotInput, output_model=SnapshotOutput),
        collect_snapshot,
    )
    registry.register(
        ToolSpec(
            name="simulate_tournament",
            input_model=SimulateInput,
            output_model=SimulateOutput,
            timeout_seconds=0.005,
            max_attempts=2,
        ),
        simulate_tournament,
    )
    return registry
