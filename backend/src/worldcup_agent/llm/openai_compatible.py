from __future__ import annotations

import asyncio
import json
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from worldcup_agent.llm.config import LLMSettings
from worldcup_agent.llm.contracts import (
    LLMAuthError,
    LLMRateLimitError,
    LLMResponseValidationError,
    LLMUnavailableError,
    LLMUsage,
    StructuredRequest,
    StructuredResponse,
)

ResponseT = TypeVar("ResponseT", bound=BaseModel)


class OpenAICompatibleProvider:
    provider_name = "openai-compatible"

    def __init__(self, settings: LLMSettings) -> None:
        self.settings = settings

    async def complete_structured(
        self, request: StructuredRequest, response_model: type[ResponseT]
    ) -> StructuredResponse:
        url = f"{self.settings.base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {self.settings.api_key.get_secret_value()}"}
        messages = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": json.dumps(request.user_payload, ensure_ascii=False)},
        ]

        content, usage, model = await self._call_with_retry(url, headers, messages, request)
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = await self._repair(url, headers, messages, content, response_model)

        try:
            value = response_model.model_validate(parsed)
        except ValidationError as exc:
            raise LLMResponseValidationError(
                f"provider response failed schema validation: {self._safe_summary(exc)}"
            ) from exc

        return StructuredResponse(
            value=value,
            provider=self.provider_name,
            model=model,
            usage=usage,
        )

    async def _call_with_retry(
        self, url, headers, messages, request: StructuredRequest
    ):
        last_error: Exception | None = None
        for attempt in range(self.settings.max_retries + 1):
            try:
                return await self._single_call(url, headers, messages, request)
            except LLMRateLimitError as exc:
                last_error = exc
                await asyncio.sleep(0.1 * (2**attempt))
            except LLMUnavailableError as exc:
                if isinstance(exc, LLMAuthError):
                    raise
                last_error = exc
                if attempt < self.settings.max_retries:
                    await asyncio.sleep(0.1 * (2**attempt))
                else:
                    raise
        raise last_error or LLMUnavailableError("exhausted retries")

    async def _single_call(self, url, headers, messages, request: StructuredRequest):
        body = {
            "model": self.settings.model,
            "messages": messages,
            "temperature": request.temperature,
        }
        async with httpx.AsyncClient(timeout=self.settings.timeout_seconds) as client:
            try:
                response = await client.post(url, headers=headers, json=body)
            except httpx.HTTPError as exc:
                raise LLMUnavailableError(f"transport error: {exc}") from exc

        if response.status_code == 401:
            raise LLMAuthError("authentication failed")
        if response.status_code in (429, 500, 502, 503, 504):
            kind = "rate limit" if response.status_code == 429 else "server error"
            if response.status_code == 429:
                raise LLMRateLimitError(kind)
            raise LLMUnavailableError(kind)
        if response.status_code != 200:
            raise LLMUnavailableError(f"unexpected status {response.status_code}")

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        usage_raw = data.get("usage", {})
        usage = LLMUsage(
            input_tokens=usage_raw.get("prompt_tokens", 0),
            output_tokens=usage_raw.get("completion_tokens", 0),
        )
        return content, usage, data.get("model", self.settings.model)

    async def _repair(self, url, headers, messages, bad_content, response_model):
        messages = [
            *messages,
            {"role": "assistant", "content": bad_content},
            {
                "role": "user",
                "content": (
                    "The previous response was not valid JSON for the required schema. "
                    "Return ONLY a JSON object matching the schema."
                ),
            },
        ]
        content, _, _ = await self._single_call(
            url,
            headers,
            messages,
            StructuredRequest(
                system_prompt="repair",
                user_payload={},
                prompt_version="repair-v1",
            ),
        )
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMResponseValidationError("provider could not produce valid JSON after repair") from exc

    @staticmethod
    def _safe_summary(exc: Exception) -> str:
        text = str(exc)
        return text[:200] if len(text) > 200 else text
