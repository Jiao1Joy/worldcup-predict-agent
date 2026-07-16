import pytest

from worldcup_agent.prediction.service import PredictionService, RuntimeModels


def test_service_returns_consistent_versioned_prediction() -> None:
    service = PredictionService(
        RuntimeModels.baseline_fixture(data_version="data-v1", model_version="model-v1")
    )
    result = service.predict("m-1", "A", "B", home_elo=1650, away_elo=1500, neutral=True)

    assert result.outcomes.home + result.outcomes.draw + result.outcomes.away == pytest.approx(1.0)
    assert result.data_version == "data-v1"
    assert result.model_version == "model-v1"
    assert result.evidence_ids == ["MATCH-m-1-PRED"]


def test_score_matrix_regions_match_fused_outcomes() -> None:
    service = PredictionService(
        RuntimeModels.baseline_fixture(data_version="data-v1", model_version="model-v1")
    )
    result = service.predict("m-2", "A", "B", home_elo=1600, away_elo=1500, neutral=False)

    matrix_home = sum(
        cell for i, row in enumerate(result.score_matrix) for j, cell in enumerate(row) if i > j
    )
    matrix_draw = sum(row[i] for i, row in enumerate(result.score_matrix) if i < len(row))
    matrix_away = 1.0 - matrix_home - matrix_draw

    assert matrix_home == pytest.approx(result.outcomes.home, abs=1e-9)
    assert matrix_draw == pytest.approx(result.outcomes.draw, abs=1e-9)
    assert matrix_away == pytest.approx(result.outcomes.away, abs=1e-9)
