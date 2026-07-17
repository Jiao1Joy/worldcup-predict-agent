import pytest

from worldcup_agent.agent.explainer import Explanation, ExplanationClaim
from worldcup_agent.agent.publisher import publish_explanation
from worldcup_agent.domain.errors import EvidenceValidationError


def test_publish_rejects_number_not_present_in_evidence() -> None:
    evidence_bundle = {"FORECAST-1": {"Spain": 0.173}}
    explanation = Explanation(
        summary="Team A is favourite",
        claims=[ExplanationClaim(text="Team A has 99% chance", value=0.99, evidence_id="FORECAST-1")],
        uncertainty="Predictions are probabilistic.",
    )
    with pytest.raises(EvidenceValidationError, match="claim value mismatch"):
        publish_explanation(explanation, evidence_bundle)


def test_publish_rejects_missing_evidence_id() -> None:
    explanation = Explanation(
        summary="ok",
        claims=[ExplanationClaim(text="x", value=0.5, evidence_id="MISSING")],
        uncertainty="u",
    )
    with pytest.raises(EvidenceValidationError, match="missing evidence"):
        publish_explanation(explanation, {})


def test_publish_renders_markdown_for_valid_claims() -> None:
    evidence_bundle = {"FORECAST-1": {"Spain": 0.173}}
    explanation = Explanation(
        summary="Spain leads",
        claims=[ExplanationClaim(text="Spain champion probability 17.3%", value=0.173, evidence_id="FORECAST-1")],
        uncertainty="Probabilistic.",
    )
    markdown = publish_explanation(explanation, evidence_bundle)
    assert "Spain leads" in markdown
    assert "FORECAST-1" in markdown
