from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from worldcup_agent.backtest.evaluator import BacktestWindow, split_backtest

FIXTURE = Path(__file__).parents[2] / "tests" / "fixtures" / "international_results_small.csv"


@pytest.fixture
def sample_matches() -> pd.DataFrame:
    frame = pd.read_csv(FIXTURE)
    frame["date"] = pd.to_datetime(frame["date"], utc=True)
    return frame


def test_2022_world_cup_is_never_in_training_partition(sample_matches) -> None:
    train, evaluation = split_backtest(
        sample_matches,
        BacktestWindow(train_end=date(2022, 11, 19), evaluation_end=date(2022, 12, 18)),
    )
    assert train["date"].max().date() <= date(2022, 11, 19)
    assert evaluation["date"].min().date() == date(2022, 11, 20)
    assert evaluation["date"].max().date() <= date(2022, 12, 18)


def test_backtest_metrics_recomputed_from_per_match_rows(sample_matches) -> None:
    from worldcup_agent.backtest.evaluator import evaluate_predictions
    from worldcup_agent.backtest.report import serialize_report

    train, evaluation = split_backtest(
        sample_matches,
        BacktestWindow(train_end=date(2022, 11, 19), evaluation_end=date(2022, 12, 18)),
    )
    metrics, per_match = evaluate_predictions(train, evaluation, data_version="data-v1", model_version="model-v1")
    report = serialize_report(metrics, per_match, output_stem="backtest-2022")

    recomputed_rps = sum(row["rps"] for row in report["per_match"]) / len(report["per_match"])
    assert recomputed_rps == pytest.approx(report["aggregate"]["rps"], abs=1e-12)
    assert len(report["per_match"]) == len(evaluation)
    assert report["aggregate"]["evaluation_matches"] == len(evaluation)
