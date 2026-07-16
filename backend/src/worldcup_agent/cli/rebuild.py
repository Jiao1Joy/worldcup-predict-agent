"""Rebuild prediction artifacts from a historical results CSV."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from worldcup_agent.artifacts.repository import ArtifactRepository
from worldcup_agent.backtest.evaluator import BacktestWindow, evaluate_predictions, split_backtest
from worldcup_agent.data.snapshot import build_snapshot
from worldcup_agent.prediction.calibration import train_baseline_calibrator
from worldcup_agent.prediction.elo import EloEngine, MatchForElo
from worldcup_agent.prediction.goal_models import fit_bivariate_poisson, fit_dixon_coles, fit_poisson


def _parse_cutoff(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _fit_goal_models(train: pd.DataFrame) -> dict:
    elo = EloEngine()
    pre_rows: list[tuple[float, float, bool, int, int]] = []
    for _, match in train.iterrows():
        home_rating = elo.rating(match["home_team"])
        away_rating = elo.rating(match["away_team"])
        pre_rows.append(
            (home_rating, away_rating, bool(match["neutral"]), int(match["home_score"]), int(match["away_score"]))
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
    home_elos = np.array([r[0] for r in pre_rows])
    away_elos = np.array([r[1] for r in pre_rows])
    neutrals = np.array([r[2] for r in pre_rows])
    home_scores = np.array([r[3] for r in pre_rows])
    away_scores = np.array([r[4] for r in pre_rows])
    return {
        "poisson": fit_poisson(home_elos, away_elos, neutrals, home_scores, away_scores),
        "bivariate_poisson": fit_bivariate_poisson(home_elos, away_elos, neutrals, home_scores, away_scores),
        "dixon_coles": fit_dixon_coles(home_elos, away_elos, neutrals, home_scores, away_scores),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild baseline prediction artifacts")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--forecast-cutoff", type=_parse_cutoff, required=True)
    parser.add_argument("--train-end", type=_parse_cutoff, required=True)
    parser.add_argument("--backtest-end", type=_parse_cutoff, required=True)
    parser.add_argument("--seed", type=int, default=20260611)
    parser.add_argument("--profile", choices=["baseline", "full"], default="baseline")
    args = parser.parse_args()

    if args.profile == "full":
        try:
            import catboost  # noqa: F401
            import lightgbm  # noqa: F401
            import xgboost  # noqa: F401
        except ImportError:
            print(
                "full profile requires the 'full-training' extras. "
                "Install with: python -m pip install -e \".[full-training]\""
            )
            return 2

    snapshot, manifest = build_snapshot(
        args.source,
        args.output / "snapshot.parquet",
        cutoff=args.forecast_cutoff,
        source_uri=str(args.source),
    )

    train_end = args.train_end.astimezone(UTC).date()
    backtest_end = args.backtest_end.astimezone(UTC).date()
    train_split, eval_split = split_backtest(
        snapshot,
        BacktestWindow(train_end=train_end, evaluation_end=backtest_end),
    )

    goal_models = _fit_goal_models(train_split)

    # Build calibration features on the evaluation window using Dixon-Coles.
    elo = EloEngine()
    for _, match in train_split.iterrows():
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

    metrics, per_match = evaluate_predictions(
        train_split,
        eval_split,
        data_version=manifest.data_version,
        model_version="rebuild-baseline",
    )

    # Train baseline calibrator on training partition outcomes.
    features = []
    labels = []
    for _, match in train_split.iterrows():
        home_rating = elo.rating(match["home_team"])
        away_rating = elo.rating(match["away_team"])
        expected = EloEngine.expected_home_score_from_ratings(home_rating, away_rating, bool(match["neutral"]))
        features.append([expected, 1 - expected])
        if match["home_score"] > match["away_score"]:
            labels.append(0)
        elif match["home_score"] < match["away_score"]:
            labels.append(2)
        else:
            labels.append(1)
    calibrator = train_baseline_calibrator(np.array(features), np.array(labels))

    repository = ArtifactRepository(args.output / "artifacts")
    artifact_manifest = repository.save_baseline(
        model=calibrator,
        data_version=manifest.data_version,
        selected_goal_model=goal_models["dixon_coles"].model_name,
        fusion_weights={"elo": 0.2, "goal": 0.5, "ml": 0.3},
        metrics={
            "rps": metrics["rps"],
            "log_loss": metrics["log_loss"],
            "brier": metrics["brier"],
        },
    )

    summary = {
        "data_version": manifest.data_version,
        "model_version": artifact_manifest.model_version,
        "goal_models": {k: v.model_dump() for k, v in goal_models.items()},
        "metrics": metrics,
    }
    (args.output / "rebuild-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    print(f"Rebuilt artifacts at {args.output} (data_version={manifest.data_version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
