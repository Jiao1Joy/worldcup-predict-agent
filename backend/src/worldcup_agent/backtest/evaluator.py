from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from worldcup_agent.prediction.elo import EloEngine
from worldcup_agent.prediction.features import elo_goal_intensities
from worldcup_agent.prediction.goal_models import dixon_coles_matrix
from worldcup_agent.prediction.metrics import ranked_probability_score


@dataclass(frozen=True)
class BacktestWindow:
    train_end: date
    evaluation_end: date


def split_backtest(matches: pd.DataFrame, window: BacktestWindow) -> tuple[pd.DataFrame, pd.DataFrame]:
    train_end = pd.Timestamp(window.train_end, tz="UTC")
    evaluation_start = train_end + pd.Timedelta(days=1)
    evaluation_end = pd.Timestamp(window.evaluation_end, tz="UTC")
    if evaluation_start > evaluation_end:
        raise ValueError("evaluation window ends before it starts")
    train = matches[matches["date"] <= train_end].copy()
    evaluation = matches[
        (matches["date"] >= evaluation_start) & (matches["date"] <= evaluation_end)
    ].copy()
    if train.empty:
        raise ValueError("training partition is empty")
    if evaluation.empty:
        raise ValueError("evaluation partition is empty")
    overlap = matches[
        (matches["date"] > train_end) & (matches["date"] < evaluation_start)
    ]
    if not overlap.empty:
        raise ValueError("training and evaluation partitions overlap")
    return train, evaluation


def _outcome_index(home_score: int, away_score: int) -> int:
    if home_score > away_score:
        return 0
    if home_score < away_score:
        return 2
    return 1


def evaluate_predictions(
    train: pd.DataFrame,
    evaluation: pd.DataFrame,
    data_version: str,
    model_version: str,
    mu: float = 0.22,
    xi: float = 0.0016,
    rho: float = -0.08,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    # Train Elo on the training partition only (no future information).
    elo = EloEngine()
    pre_match_ratings: dict[tuple[str, str], tuple[float, float]] = {}
    for _, match in train.iterrows():
        from worldcup_agent.prediction.elo import MatchForElo

        pre_match_ratings[(match["home_team"], match["away_team"])] = (
            elo.rating(match["home_team"]),
            elo.rating(match["away_team"]),
        )
        elo.process(
            MatchForElo(
                home_team=match["home_team"],
                away_team=match["away_team"],
                home_score=int(match["home_score"]),
                away_score=int(match["away_score"]),
                tournament=str(match["tournament"]),
                neutral=bool(match["neutral"]),
            )
        )

    per_match: list[dict[str, Any]] = []
    probabilities: list[list[float]] = []
    outcomes: list[int] = []
    for _, match in evaluation.iterrows():
        home_rating = elo.rating(match["home_team"])
        away_rating = elo.rating(match["away_team"])
        neutral = bool(match["neutral"])
        home_lambda, away_lambda = elo_goal_intensities(home_rating, away_rating, neutral, mu, xi)
        home_lambda = float(np.clip(home_lambda, 0.05, 12.0))
        away_lambda = float(np.clip(away_lambda, 0.05, 12.0))
        matrix = dixon_coles_matrix(home_lambda, away_lambda, rho, max_goals=8)
        home = sum(
            float(matrix[i, j]) for i in range(matrix.shape[0]) for j in range(matrix.shape[1]) if i > j
        )
        draw = sum(float(matrix[i, i]) for i in range(min(matrix.shape)))
        away = 1.0 - home - draw
        probs = [home, draw, away]
        probabilities.append(probs)
        outcome = _outcome_index(int(match["home_score"]), int(match["away_score"]))
        outcomes.append(outcome)
        per_match.append(
            {
                "match_id": str(match.get("match_id", "")),
                "date": str(match["date"].date()),
                "home_team": match["home_team"],
                "away_team": match["away_team"],
                "home_score": int(match["home_score"]),
                "away_score": int(match["away_score"]),
                "outcome": ["home", "draw", "away"][outcome],
                "home_probability": home,
                "draw_probability": draw,
                "away_probability": away,
                "predicted_outcome": ["home", "draw", "away"][int(np.argmax(probs))],
                "rps": ranked_probability_score(probs, outcome),
            }
        )

    probabilities_arr = np.array(probabilities)
    outcomes_arr = np.array(outcomes)
    n = len(outcomes)

    # Multiclass log loss.
    eps = 1e-15
    log_loss = -sum(
        np.log(max(probabilities_arr[i, outcomes_arr[i]], eps)) for i in range(n)
    ) / n

    # Multiclass Brier (sum of squared errors over classes, averaged).
    one_hot = np.zeros_like(probabilities_arr)
    one_hot[np.arange(n), outcomes_arr] = 1.0
    brier = float(np.mean(np.sum((probabilities_arr - one_hot) ** 2, axis=1)))

    accuracy = float(np.mean(np.argmax(probabilities_arr, axis=1) == outcomes_arr))
    mean_rps = float(np.mean([row["rps"] for row in per_match]))

    # Ten equal-width calibration bins on the predicted home probability.
    bins = np.linspace(0, 1, 11)
    bin_indices = np.digitize(probabilities_arr[:, 0], bins) - 1
    bin_indices = np.clip(bin_indices, 0, 9)
    calibration_bins = []
    for b in range(10):
        mask = bin_indices == b
        if mask.any():
            predicted = float(probabilities_arr[mask, 0].mean())
            observed = float(one_hot[mask, 0].mean())
            calibration_bins.append(
                {"bin": b, "predicted": predicted, "observed": observed, "count": int(mask.sum())}
            )

    metrics = {
        "data_version": data_version,
        "model_version": model_version,
        "evaluation_matches": n,
        "rps": mean_rps,
        "log_loss": float(log_loss),
        "brier": brier,
        "accuracy": accuracy,
        "calibration_bins": calibration_bins,
    }
    return metrics, per_match
