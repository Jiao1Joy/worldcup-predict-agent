from __future__ import annotations

import os

from pydantic import BaseModel, SecretStr


class LLMSettings(BaseModel):
    enabled: bool = False
    base_url: str = ""
    api_key: SecretStr = SecretStr("")
    model: str = "fixed-model-id"
    timeout_seconds: float = 30.0
    max_retries: int = 2

    def __repr__(self) -> str:
        return (
            f"LLMSettings(enabled={self.enabled}, base_url={self.base_url!r}, "
            f"model={self.model!r}, api_key=***)"
        )

    @classmethod
    def from_env(cls) -> LLMSettings:
        enabled = os.environ.get("WORLDCUP_LLM_ENABLED", "").lower() in ("1", "true", "yes")
        api_key = os.environ.get("WORLDCUP_LLM_API_KEY", "")
        model = os.environ.get("WORLDCUP_LLM_MODEL", "fixed-model-id")
        if model == "latest":
            raise ValueError("WORLDCUP_LLM_MODEL must be an explicit model id, not 'latest'")
        if enabled and not api_key:
            enabled = False
        return cls(
            enabled=enabled,
            base_url=os.environ.get("WORLDCUP_LLM_BASE_URL", ""),
            api_key=SecretStr(api_key),
            model=model,
            timeout_seconds=float(os.environ.get("WORLDCUP_LLM_TIMEOUT_SECONDS", "30")),
            max_retries=int(os.environ.get("WORLDCUP_LLM_MAX_RETRIES", "2")),
        )
