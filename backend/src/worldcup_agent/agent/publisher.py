from __future__ import annotations

from math import isclose

from worldcup_agent.agent.explainer import Explanation, ExplanationClaim
from worldcup_agent.domain.errors import EvidenceValidationError


def publish_explanation(explanation: Explanation, evidence_bundle: dict) -> str:
    """Validate every numeric claim against the evidence bundle and render a summary.

    Raises ``EvidenceValidationError`` when any claim references a missing
    evidence id, a mismatched numeric value, or when the explanation omits the
    uncertainty disclosure.
    """
    if not explanation.uncertainty:
        raise EvidenceValidationError("explanation must include an uncertainty disclosure")

    for claim in explanation.claims:
        if claim.evidence_id not in evidence_bundle:
            raise EvidenceValidationError(f"missing evidence: {claim.evidence_id}")
        if claim.value is None:
            continue
        values = evidence_bundle[claim.evidence_id]
        if not _claim_matches(claim.value, values):
            raise EvidenceValidationError(f"claim value mismatch: {claim.evidence_id}")

    return _render_markdown(explanation)


def _claim_matches(value: float, evidence_value) -> bool:
    if isinstance(evidence_value, dict):
        return any(
            isinstance(v, (int, float)) and isclose(v, value, abs_tol=1e-9)
            for v in evidence_value.values()
        )
    if isinstance(evidence_value, list):
        return any(
            isinstance(v, (int, float)) and isclose(v, value, abs_tol=1e-9)
            for v in evidence_value
        )
    if isinstance(evidence_value, (int, float)):
        return isclose(evidence_value, value, abs_tol=1e-9)
    return False


def _render_markdown(explanation: Explanation) -> str:
    lines = [f"# {explanation.summary}", "", explanation.uncertainty, ""]
    if explanation.claims:
        lines.append("| Claim | Evidence |")
        lines.append("| --- | --- |")
        for claim in explanation.claims:
            lines.append(f"| {claim.text} | `{claim.evidence_id}` |")
    return "\n".join(lines)


def template_explanation(
    champion_team: str,
    champion_probability: float,
    forecast_evidence_id: str,
    convergence_delta: float,
    convergence_evidence_id: str,
    backtest_rps: float,
    backtest_evidence_id: str,
    data_version: str,
    model_version: str,
    rules_version: str,
) -> Explanation:
    return Explanation(
        summary=f"{champion_team} has the highest modeled probability of winning the tournament "
        f"({champion_probability:.1%}).",
        claims=[
            ExplanationClaim(
                text=f"{champion_team} champion probability {champion_probability:.1%}",
                value=champion_probability,
                unit="probability",
                evidence_id=forecast_evidence_id,
            ),
            ExplanationClaim(
                text=f"Monte Carlo convergence delta {convergence_delta:.4f}",
                value=convergence_delta,
                unit="probability",
                evidence_id=convergence_evidence_id,
            ),
            ExplanationClaim(
                text=f"2022 backtest RPS {backtest_rps:.4f}",
                value=backtest_rps,
                unit="rps",
                evidence_id=backtest_evidence_id,
            ),
        ],
        uncertainty=(
            "Probabilities are model estimates, not certainties. Outcomes depend on events "
            "the model cannot observe, including injuries, tactics, and chance."
        ),
        data_version=data_version,
        model_version=model_version,
        rules_version=rules_version,
    )
