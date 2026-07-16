from __future__ import annotations

from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

ResponseT = TypeVar("ResponseT", bound=BaseModel)


class StructuredRequest(BaseModel):
    system_prompt: str
    user_payload: dict[str, Any]
    prompt_version: str
    temperature: float = 0.0


class LLMUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class StructuredResponse(BaseModel):
    value: BaseModel
    provider: str
    model: str
    usage: LLMUsage


class LLMProvider(Protocol):
    async def complete_structured(
        self, request: StructuredRequest, response_model: type[ResponseT]
    ) -> StructuredResponse: ...


class LLMUnavailableError(Exception):
    pass


class LLMAuthError(LLMUnavailableError):
    """Authentication failure (e.g. HTTP 401). Never retried."""
    pass


class LLMResponseValidationError(Exception):
    pass


class LLMRateLimitError(Exception):
    pass
