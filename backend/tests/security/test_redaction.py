from worldcup_agent.security.redaction import redact


def test_redact_drops_api_key_and_authorization() -> None:
    payload = {
        "api_key": "secret-value",
        "authorization": "Bearer abc123",
        "prompt": "system prompt text",
        "safe": "ok",
        "nested": {"token": "tok", "value": 1},
    }
    redacted = redact(payload, known_secrets={"secret-value"})
    assert redacted["api_key"] == "***"
    assert redacted["authorization"] == "***"
    assert redacted["prompt"] == "***"
    assert redacted["safe"] == "ok"
    assert redacted["nested"]["token"] == "***"
    assert "secret-value" not in str(redacted)


def test_redact_keeps_error_metadata() -> None:
    event = {
        "error_type": "timeout",
        "retryable": True,
        "attempt": 2,
        "provider": "openai-compatible",
        "correlation_id": "abc",
        "api_key": "leaked",
    }
    redacted = redact(event, known_secrets={"leaked"})
    assert redacted["error_type"] == "timeout"
    assert redacted["retryable"] is True
    assert redacted["attempt"] == 2
    assert redacted["provider"] == "openai-compatible"
    assert redacted["correlation_id"] == "abc"
    assert "leaked" not in str(redacted)


def test_redact_handles_lists_and_plain_strings() -> None:
    assert redact(["Bearer xyz", "safe"]) == ["***", "safe"]
    assert redact("sk-" + "a" * 20) == "***"
