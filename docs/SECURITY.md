# Security

## Secrets

- The LLM API key is read **only** from the `WORLDCUP_LLM_API_KEY` environment variable.
- It is never written to disk, logs, events, fixtures, or HTTP responses.
- `.env` is gitignored; `.env.example` ships with an empty key.
- `LLMSettings` stores the key as a Pydantic `SecretStr` and redacts it from `repr`.

## Outbound hosts

- Production Portfolio mode makes **zero** outbound network calls (offline fixtures).
- Rebuild mode downloads nothing — it reads the committed `results.csv`.
- Live LLM mode (optional) calls only the configured `WORLDCUP_LLM_BASE_URL`.

## Prompt retention

- Prompts are never persisted. The `prompt` key is redacted from all events.
- No hidden chain-of-thought is stored or surfaced; only structured Decision Records and Evidence are kept.

## Event redaction

`worldcup_agent.security.redaction.redact` recursively scrubs keys matching `api_key`, `authorization`, `token`, `secret`, and `prompt`, plus known configured secret values and bearer tokens. It is applied before logging, event persistence, HTTP error serialization, and fixture generation.

## Reporting

Report vulnerabilities by opening a private advisory. Do not file public issues for security problems.
