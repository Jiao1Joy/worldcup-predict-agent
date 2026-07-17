from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class KnockoutResult:
    winner: str
    runner_up: str
    home_goals: int
    away_goals: int
    decided_by: str  # "regular_time" | "extra_time" | "penalties"


def sample_group_score(matrix: np.ndarray, rng: np.random.Generator) -> tuple[int, int]:
    flat = matrix.flatten()
    total = flat.sum()
    if total <= 0:
        raise ValueError("score matrix has no probability mass")
    flat = flat / total
    index = rng.choice(flat.size, p=flat)
    side = matrix.shape[0]
    return int(index // side), int(index % side)


def sample_knockout_winner(
    home_team: str,
    away_team: str,
    matrix: np.ndarray,
    rng: np.random.Generator,
    penalty_home_probability: float = 0.5,
    expected_home_goals: float | None = None,
    expected_away_goals: float | None = None,
) -> KnockoutResult:
    home_goals, away_goals = sample_group_score(matrix, rng)
    decided_by = "regular_time"

    if home_goals == away_goals:
        # Extra time: sample from reduced intensity Poisson-like goals.
        home_rate = max(expected_home_goals / 3.0, 0.15) if expected_home_goals else 0.3
        away_rate = max(expected_away_goals / 3.0, 0.15) if expected_away_goals else 0.3
        et_home = int(rng.poisson(home_rate))
        et_away = int(rng.poisson(away_rate))
        if et_home != et_away:
            home_goals += et_home
            away_goals += et_away
            decided_by = "extra_time"
        else:
            decided_by = "penalties"
            if rng.random() < penalty_home_probability:
                winner, runner_up = home_team, away_team
            else:
                winner, runner_up = away_team, home_team
            return KnockoutResult(winner, runner_up, home_goals + et_home, away_goals + et_away, decided_by)

    if home_goals > away_goals:
        winner, runner_up = home_team, away_team
    else:
        winner, runner_up = away_team, home_team
    return KnockoutResult(winner, runner_up, home_goals, away_goals, decided_by)
