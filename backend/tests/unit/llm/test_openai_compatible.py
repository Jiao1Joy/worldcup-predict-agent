import httpx
import pytest
import respx
from pydantic import BaseModel

from worldcup_agent.llm.config import LLMSettings
from worldcup_agent.llm.contracts import (
    LLMResponseValidationError,
    LLMUnavailableError,
)
from worldcup_agent.llm.contracts import StructuredRequest
from worldcup_agent.llm.openai_compatible import OpenAICompatibleProvider


class Choice(BaseModel):
    action: str


@pytest.fixture
def settings() -> LLMSettings:
    return LLMSettings(
        enabled=True,
        base_url="https://provider.example/v1",
        api_key="test-key",
        model="fixed-model-id",
        max_retries=1,
        timeout_seconds=2.0,
    )


@pytest.fixture
def structured_request() -> StructuredRequest:
    return StructuredRequest(
        system_prompt="plan",
        user_payload={"task": "predict"},
        prompt_version="planner-v1",
    )


@respx.mock
@pytest.mark.asyncio
async def test_adapter_parses_structured_json(settings, structured_request) -> None:
    respx.post("https://provider.example/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={
            "choices": [{"message": {"content": '{"action":"simulate"}'}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 4},
        })
    )
    provider = OpenAICompatibleProvider(settings)
    response = await provider.complete_structured(structured_request, Choice)
    assert response.value.action == "simulate"
    assert response.usage.input_tokens == 10


@respx.mock
@pytest.mark.asyncio
async def test_adapter_repairs_invalid_json_then_succeeds(settings, structured_request) -> None:
    respx.post("https://provider.example/v1/chat/completions").mock(
        side_effect=[
            httpx.Response(200, json={"choices": [{"message": {"content": "not json"}}]}),
            httpx.Response(200, json={"choices": [{"message": {"content": '{"action":"simulate"}'}}]}),
        ]
    )
    provider = OpenAICompatibleProvider(settings)
    response = await provider.complete_structured(structured_request, Choice)
    assert response.value.action == "simulate"


@respx.mock
@pytest.mark.asyncio
async def test_persistent_invalid_json_raises_validation_error(settings, structured_request) -> None:
    respx.post("https://provider.example/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": "still not json"}}]})
    )
    provider = OpenAICompatibleProvider(settings)
    with pytest.raises(LLMResponseValidationError):
        await provider.complete_structured(structured_request, Choice)


@respx.mock
@pytest.mark.asyncio
async def test_http_401_not_retried(settings, structured_request) -> None:
    respx.post("https://provider.example/v1/chat/completions").mock(
        return_value=httpx.Response(401)
    )
    provider = OpenAICompatibleProvider(settings)
    with pytest.raises(LLMUnavailableError):
        await provider.complete_structured(structured_request, Choice)
    assert respx.calls.call_count == 1


@respx.mock
@pytest.mark.asyncio
async def test_server_error_retries(settings, structured_request) -> None:
    respx.post("https://provider.example/v1/chat/completions").mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, json={"choices": [{"message": {"content": '{"action":"simulate"}'}}]}),
        ]
    )
    provider = OpenAICompatibleProvider(settings)
    response = await provider.complete_structured(structured_request, Choice)
    assert response.value.action == "simulate"
    assert respx.calls.call_count == 2
