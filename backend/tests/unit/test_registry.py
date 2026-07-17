import asyncio

import pytest
from pydantic import BaseModel

from worldcup_agent.domain.errors import ToolTimeoutError, ToolValidationError
from worldcup_agent.tools.contracts import ToolContext, ToolSpec
from worldcup_agent.tools.demo import build_demo_registry
from worldcup_agent.tools.registry import ToolRegistry


class EchoInput(BaseModel):
    value: int


class EchoOutput(BaseModel):
    doubled: int


@pytest.mark.asyncio
async def test_registry_validates_and_executes_tool() -> None:
    registry = ToolRegistry()

    async def echo(payload: EchoInput, _: ToolContext) -> EchoOutput:
        return EchoOutput(doubled=payload.value * 2)

    registry.register(ToolSpec(name="echo", input_model=EchoInput, output_model=EchoOutput), echo)
    result = await registry.execute("echo", {"value": 4}, ToolContext(run_id="r", step_id="s"))

    assert result.output == {"doubled": 8}
    assert result.attempts == 1


@pytest.mark.asyncio
async def test_registry_rejects_invalid_input() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolSpec(name="echo", input_model=EchoInput, output_model=EchoOutput),
        lambda payload, context: EchoOutput(doubled=payload.value * 2),
    )

    with pytest.raises(ToolValidationError):
        await registry.execute("echo", {"value": "bad"}, ToolContext(run_id="r", step_id="s"))


@pytest.mark.asyncio
async def test_registry_retries_timeout() -> None:
    registry = ToolRegistry()

    async def slow(payload: EchoInput, _: ToolContext) -> EchoOutput:
        await asyncio.sleep(0.02)
        return EchoOutput(doubled=payload.value * 2)

    registry.register(
        ToolSpec(
            name="slow",
            input_model=EchoInput,
            output_model=EchoOutput,
            timeout_seconds=0.001,
            max_attempts=2,
        ),
        slow,
    )

    with pytest.raises(ToolTimeoutError):
        await registry.execute("slow", {"value": 2}, ToolContext(run_id="r", step_id="s"))


@pytest.mark.asyncio
async def test_demo_simulator_is_reproducible() -> None:
    registry = build_demo_registry()
    context = ToolContext(run_id="r", step_id="simulate")

    first = await registry.execute("simulate_tournament", {"runs": 1000, "seed": 7}, context)
    second = await registry.execute("simulate_tournament", {"runs": 1000, "seed": 7}, context)

    assert first.output == second.output
    assert sum(first.output["champion_probabilities"].values()) == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_demo_simulator_can_inject_timeout() -> None:
    registry = build_demo_registry()
    context = ToolContext(
        run_id="r",
        step_id="simulate",
        metadata={"inject_failure": "timeout"},
    )

    with pytest.raises(ToolTimeoutError):
        await registry.execute("simulate_tournament", {"runs": 1000, "seed": 7}, context)
