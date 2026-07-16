import asyncio
import inspect
from time import perf_counter

from pydantic import ValidationError

from worldcup_agent.domain.errors import ToolTimeoutError, ToolValidationError
from worldcup_agent.tools.contracts import (
    ToolContext,
    ToolExecutionResult,
    ToolHandler,
    ToolSpec,
)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, tuple[ToolSpec, ToolHandler]] = {}

    def register(self, spec: ToolSpec, handler: ToolHandler) -> None:
        if spec.name in self._tools:
            raise ValueError(f"tool already registered: {spec.name}")
        self._tools[spec.name] = (spec, handler)

    def get_spec(self, name: str) -> ToolSpec:
        try:
            return self._tools[name][0]
        except KeyError as exc:
            raise KeyError(f"unknown tool: {name}") from exc

    async def execute(
        self,
        name: str,
        raw_input: dict,
        context: ToolContext,
    ) -> ToolExecutionResult:
        spec, handler = self._tools[name]
        try:
            payload = spec.input_model.model_validate(raw_input)
        except ValidationError as exc:
            raise ToolValidationError(str(exc)) from exc

        started = perf_counter()
        for attempt in range(1, spec.max_attempts + 1):
            try:
                value = handler(payload, context)
                if inspect.isawaitable(value):
                    value = await asyncio.wait_for(value, timeout=spec.timeout_seconds)
                output = spec.output_model.model_validate(value).model_dump(mode="json")
                return ToolExecutionResult(
                    output=output,
                    attempts=attempt,
                    latency_ms=int((perf_counter() - started) * 1000),
                )
            except TimeoutError as exc:
                if attempt == spec.max_attempts:
                    raise ToolTimeoutError(f"tool {name} timed out after {attempt} attempts") from exc
        raise AssertionError("retry loop exited unexpectedly")
