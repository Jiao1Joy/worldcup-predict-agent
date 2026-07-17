from worldcup_agent.llm.config import LLMSettings


def test_settings_redact_api_key() -> None:
    settings = LLMSettings(
        enabled=True,
        base_url="https://provider.example/v1",
        api_key="secret-value",
        model="fixed-model-id",
    )
    assert "secret-value" not in repr(settings)
    assert settings.model == "fixed-model-id"


def test_missing_key_disables_live_provider(monkeypatch) -> None:
    monkeypatch.delenv("WORLDCUP_LLM_API_KEY", raising=False)
    monkeypatch.setenv("WORLDCUP_LLM_ENABLED", "true")
    settings = LLMSettings.from_env()
    assert settings.enabled is False
