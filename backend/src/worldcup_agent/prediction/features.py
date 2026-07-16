from math import exp


def elo_goal_intensities(
    home_elo: float,
    away_elo: float,
    neutral: bool,
    mu: float,
    xi: float,
    home_goal_advantage: float = 0.08,
) -> tuple[float, float]:
    difference = (home_elo - away_elo) / 2.0
    adjustment = 0.0 if neutral else home_goal_advantage
    return exp(mu + xi * difference + adjustment), exp(mu - xi * difference)
