from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel, Field


class ToolContext(BaseModel):
    run_id: str
    step_id: str
    checkpoint_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolSpec(BaseModel):
    name: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    timeout_seconds: float = Field(default=30, gt=0)
    max_attempts: int = Field(default=3, ge=1)
    fallback: str | None = None
    idempotent: bool = True
    side_effect: str = "none"

    model_config = {"arbitrary_types_allowed": True}


class ToolExecutionResult(BaseModel):
    output: dict[str, Any]
    attempts: int
    latency_ms: int


ToolHandler = Callable[[BaseModel, ToolContext], Awaitable[BaseModel] | BaseModel]
