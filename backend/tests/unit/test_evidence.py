import pytest

from worldcup_agent.domain.errors import EvidenceValidationError
from worldcup_agent.domain.models import EvidenceItem
from worldcup_agent.evidence.critic import critic_verdict
from worldcup_agent.evidence.validator import validate_claims


def test_claims_require_existing_matching_evidence() -> None:
    evidence = {
        "SIM-030": EvidenceItem(
            evidence_id="SIM-030",
            kind="champion_probability",
            value={"Spain": 0.173},
            source="TournamentSimulator",
            version="3.1",
        )
    }
    validate_claims(
        [{"text": "Spain champion probability", "value": 0.173, "evidence_id": "SIM-030"}],
        evidence,
    )


def test_mismatched_evidence_value_is_rejected() -> None:
    evidence = {
        "SIM-030": EvidenceItem(
            evidence_id="SIM-030",
            kind="champion_probability",
            value={"Spain": 0.173},
            source="TournamentSimulator",
            version="3.1",
        )
    }
    with pytest.raises(EvidenceValidationError):
        validate_claims(
            [{"text": "Spain champion probability", "value": 0.20, "evidence_id": "SIM-030"}],
            evidence,
        )


def test_critic_requests_more_simulation_when_not_converged() -> None:
    verdict = critic_verdict(probability_delta=0.018, evidence_valid=True)
    assert verdict.recommended_action == "simulate_more"
