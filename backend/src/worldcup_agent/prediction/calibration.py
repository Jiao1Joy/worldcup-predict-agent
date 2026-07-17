import numpy as np
from sklearn.linear_model import LogisticRegression

from worldcup_agent.prediction.elo import EloEngine
from worldcup_agent.prediction.features import elo_goal_intensities
from worldcup_agent.prediction.goal_models import GoalModelParameters, dixon_coles_matrix


def outcome_probabilities(matrix: np.ndarray) -> np.ndarray:
    home = sum(
        float(cell) for i, row in enumerate(matrix) for j, cell in enumerate(row) if i > j
    )
    draw = sum(float(matrix[i, i]) for i in range(min(matrix.shape)))
    return np.array([home, draw, 1.0 - home - draw], dtype=float)


def calibration_features(
    home_elo: float,
    away_elo: float,
    neutral: bool,
    goal_parameters: GoalModelParameters,
    max_goals: int = 8,
) -> np.ndarray:
    """Build the single feature contract shared by training and inference."""
    expected = EloEngine.expected_home_score_from_ratings(home_elo, away_elo, neutral)
    draw = 0.27
    elo = np.array([expected * (1 - draw), draw, (1 - expected) * (1 - draw)])
    home_lambda, away_lambda = elo_goal_intensities(
        home_elo, away_elo, neutral, goal_parameters.mu, goal_parameters.xi
    )
    goal = outcome_probabilities(
        dixon_coles_matrix(home_lambda, away_lambda, goal_parameters.rho, max_goals=max_goals)
    )
    return np.concatenate([elo / elo.sum(), goal / goal.sum()])


def train_baseline_calibrator(features, labels):
    model = LogisticRegression(max_iter=2000, random_state=20260611)
    return model.fit(features, labels)
