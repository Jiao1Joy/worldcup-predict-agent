from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from worldcup_agent.prediction.contracts import MatchPrediction
from worldcup_agent.prediction.calibration import calibration_features, outcome_probabilities
from worldcup_agent.prediction.elo import EloEngine
from worldcup_agent.prediction.features import elo_goal_intensities
from worldcup_agent.prediction.goal_models import GoalModelParameters, dixon_coles_matrix


@dataclass
class RuntimeModels:
    goal_parameters: GoalModelParameters
    fusion_weights: dict[str, float]
    data_version: str
    model_version: str
    baseline: object = None
    max_goals: int = 8

    @classmethod
    def baseline_fixture(
        cls,
        data_version: str,
        model_version: str,
        max_goals: int = 8,
    ) -> RuntimeModels:
        goal_parameters = GoalModelParameters(
            model_name="dixon_coles",
            mu=0.22,
            xi=0.0016,
            rho=-0.08,
            objective=0.0,
            converged=True,
        )
        weights = {"elo": 0.2, "goal": 0.5, "ml": 0.3}
        return cls(
            goal_parameters=goal_parameters,
            fusion_weights=weights,
            data_version=data_version,
            model_version=model_version,
            baseline=None,
            max_goals=max_goals,
        )


def _matrix_outcomes(matrix: np.ndarray) -> tuple[float, float, float]:
    return tuple(outcome_probabilities(matrix))


def _reconcile_matrix(matrix: np.ndarray, home: float, draw: float, away: float) -> np.ndarray:
    """Iterative proportional fitting so score-matrix regions match fused outcomes."""
    target = np.array([home, draw, away], dtype=float)
    matrix = matrix.copy()
    for _ in range(100):
        current = np.array(_matrix_outcomes(matrix), dtype=float)
        error = np.abs(current - target)
        if np.all(error < 1e-9):
            return matrix
        # Scale each region toward its target. Guard against zero-mass regions.
        for region_index, (cur, tgt) in enumerate(zip(current, target, strict=True)):
            if cur <= 0:
                continue
            factor = tgt / cur
            if region_index == 0:  # home win region: lower triangle
                for i in range(matrix.shape[0]):
                    for j in range(matrix.shape[1]):
                        if i > j:
                            matrix[i, j] *= factor
            elif region_index == 1:  # draw: diagonal
                for i in range(min(matrix.shape)):
                    matrix[i, i] *= factor
            else:  # away win: upper triangle
                for i in range(matrix.shape[0]):
                    for j in range(matrix.shape[1]):
                        if i < j:
                            matrix[i, j] *= factor
        matrix = matrix / matrix.sum()
    current = np.array(_matrix_outcomes(matrix), dtype=float)
    if np.any(np.abs(current - target) >= 1e-9):
        raise RuntimeError("score matrix reconciliation did not converge")
    return matrix


class PredictionService:
    def __init__(self, models: RuntimeModels) -> None:
        self.models = models
        self._elo = EloEngine()

    def predict(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        home_elo: float,
        away_elo: float,
        neutral: bool,
    ) -> MatchPrediction:
        params = self.models.goal_parameters

        # 1. Elo prior outcome probabilities.
        features = calibration_features(
            home_elo, away_elo, neutral, params, max_goals=self.models.max_goals
        )
        elo_probs = features[:3]

        # 2. Elo-driven expected goals.
        home_lambda, away_lambda = elo_goal_intensities(
            home_elo, away_elo, neutral, params.mu, params.xi
        )

        # 3. Score matrix from selected goal model.
        matrix = dixon_coles_matrix(home_lambda, away_lambda, params.rho, max_goals=self.models.max_goals)

        # 4. Goal-model outcome probabilities from the matrix.
        goal_home, goal_draw, goal_away = _matrix_outcomes(matrix)
        goal_probs = np.array([goal_home, goal_draw, goal_away], dtype=float)
        goal_probs = goal_probs / goal_probs.sum()

        # 5. Baseline calibrator features (Elo + goal priors); when no trained
        #    calibrator is available, fall back to the goal-model probabilities.
        if self.models.baseline is not None:
            features = features.reshape(1, -1)
            classes = list(self.models.baseline.classes_)
            proba = self.models.baseline.predict_proba(features)[0]
            ml_probs = np.array([0.0, 0.0, 0.0], dtype=float)
            for cls, p in zip(classes, proba, strict=True):
                ml_probs[cls] = p
            ml_probs = ml_probs / ml_probs.sum()
        else:
            ml_probs = goal_probs.copy()

        # 6. Fuse Elo, goal, and ML probabilities.
        weights = self.models.fusion_weights
        fused = (
            weights["elo"] * elo_probs
            + weights["goal"] * goal_probs
            + weights["ml"] * ml_probs
        )
        fused = fused / fused.sum()

        # 7. Reconcile score matrix to the fused outcomes via IPF.
        reconciled = _reconcile_matrix(matrix, fused[0], fused[1], fused[2])

        return MatchPrediction.from_score_matrix(
            match_id=match_id,
            home_team=home_team,
            away_team=away_team,
            expected_home_goals=float(home_lambda),
            expected_away_goals=float(away_lambda),
            score_matrix=reconciled.tolist(),
            data_version=self.models.data_version,
            model_version=self.models.model_version,
            evidence_ids=[f"MATCH-{match_id}-PRED"],
        )
