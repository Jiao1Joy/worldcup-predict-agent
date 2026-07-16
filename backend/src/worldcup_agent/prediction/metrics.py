def ranked_probability_score(probabilities: list[float], outcome_index: int) -> float:
    observed = [1.0 if index == outcome_index else 0.0 for index in range(3)]
    return 0.5 * sum(
        (sum(probabilities[: boundary + 1]) - sum(observed[: boundary + 1])) ** 2
        for boundary in range(2)
    )


def select_goal_model(scores: dict[str, float], epsilon: float = 0.001) -> str:
    best = min(scores, key=scores.get)
    if scores["bivariate_poisson"] <= scores["dixon_coles"] + epsilon:
        return "bivariate_poisson"
    return best
