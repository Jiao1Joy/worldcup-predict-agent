"""Centralized secret redaction for logs, events, and HTTP error responses."""

from __future__ import annotations

import re
from typing import Any

_SENSITIVE_KEYS = {"api_key", "apikey", "authorization", "token", "secret", "prompt"}
_VALUE_PATTERNS = [
    re.compile(r"Bearer\s+\S+"),
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"[A-Za-z]:\\[Uu]sers\\.*"),
]


def redact(value: Any, known_secrets: set[str] | None = None) -> Any:
    """Recursively redact sensitive keys and known secret values."""
    known = known_secrets or set()
    if isinstance(value, dict):
        return {k: ("***" if k.lower() in _SENSITIVE_KEYS else redact(v, known)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(item, known) for item in value]
    if isinstance(value, str):
        redacted = value
        for secret in known:
            if secret and secret in redacted:
                redacted = redacted.replace(secret, "***")
        for pattern in _VALUE_PATTERNS:
            redacted = pattern.sub("***", redacted)
        return redacted
    return value
