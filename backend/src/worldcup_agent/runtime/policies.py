def snapshot_action(age_hours: float) -> str:
    return "refresh_snapshot" if age_hours > 24 else "continue"


def next_simulation_action(probability_delta: float, total_runs: int) -> str:
    if probability_delta > 0.005 and total_runs < 50_000:
        return "simulate_more"
    return "critique"


def critic_action(model_disagreement: float, evidence_valid: bool) -> str:
    if not evidence_valid:
        return "repair_evidence"
    if model_disagreement > 0.06:
        return "run_critic"
    return "explain"
