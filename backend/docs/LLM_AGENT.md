# LLM Agent Integration

## Architecture

A single Orchestrator drives a LangGraph state graph over a contract-enforcing Tool Registry. The LLM never calculates probabilities, scores, or rankings — it only parses tasks, plans steps, and explains results. All numerical outputs come from deterministic Python services.

## Provider adapter

`OpenAICompatibleProvider` talks to any OpenAI-compatible endpoint (DeepSeek, GLM, OpenAI, etc.) via `WORLDCUP_LLM_*` environment variables. Configuration:

- `WORLDCUP_LLM_ENABLED` — must be `true` AND a key present to enable live calls.
- `WORLDCUP_LLM_MODEL` — must be an explicit model id; `latest` is rejected.
- `WORLDCUP_LLM_API_KEY` — read only from the environment, never logged.

Behavior:
- HTTP 401 → `LLMAuthError`, never retried.
- HTTP 429/5xx → retried with exponential backoff up to `max_retries`.
- Invalid JSON / schema failure → exactly one repair attempt; persistent failure raises `LLMResponseValidationError`.
- No hidden chain-of-thought is stored or surfaced in events.

## Deterministic fallback

When no key is configured (or the provider fails), `AgentPlanner(provider=None)` produces the allowlisted step sequence and a template explainer. The system still completes a full 104-match forecast. Provider failures emit a `GUARDRAIL` event and degrade to deterministic planning.

## Tool Registry

`build_production_registry` exposes `inspect_snapshot`, `predict_match`, `simulate_tournament`, `load_backtest`, `retrieve_evidence`. No handler imports FastAPI or an LLM SDK. The Registry is the only path from the Agent to domain services.

## Evidence enforcement

Every published numeric claim must reference an evidence id whose value matches within `1e-9`. The publisher rejects missing or mismatched evidence and never creates a published read model on failure.
