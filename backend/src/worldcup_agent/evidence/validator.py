from math import isclose

from worldcup_agent.domain.errors import EvidenceValidationError
from worldcup_agent.domain.models import EvidenceItem


def validate_claims(claims: list[dict], evidence: dict[str, EvidenceItem]) -> None:
    for claim in claims:
        evidence_id = claim["evidence_id"]
        if evidence_id not in evidence:
            raise EvidenceValidationError(f"missing evidence: {evidence_id}")
        values = evidence[evidence_id].value
        if not isinstance(values, dict):
            raise EvidenceValidationError(f"unsupported evidence value: {evidence_id}")
        matched = any(
            isinstance(value, (int, float)) and isclose(value, claim["value"], abs_tol=1e-9)
            for value in values.values()
        )
        if not matched:
            raise EvidenceValidationError(f"claim value mismatch: {evidence_id}")
