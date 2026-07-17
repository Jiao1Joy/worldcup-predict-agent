from pydantic import BaseModel, Field


class CriticVerdict(BaseModel):
    passed: bool
    issues: list[str] = Field(default_factory=list)
    recommended_action: str
    params: dict = Field(default_factory=dict)


def critic_verdict(probability_delta: float, evidence_valid: bool) -> CriticVerdict:
    if not evidence_valid:
        return CriticVerdict(
            passed=False,
            issues=["evidence_invalid"],
            recommended_action="repair_evidence",
        )
    if probability_delta > 0.005:
        return CriticVerdict(
            passed=False,
            issues=["simulation_not_converged"],
            recommended_action="simulate_more",
            params={"additional_runs": 10_000},
        )
    return CriticVerdict(passed=True, recommended_action="explain")
