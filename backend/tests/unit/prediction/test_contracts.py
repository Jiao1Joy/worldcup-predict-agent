import pytest
from pydantic import ValidationError

from worldcup_agent.prediction.contracts import MatchPrediction, OutcomeProbabilities


def test_match_prediction_requires_normalized_probabilities() -> None:
    prediction = MatchPrediction.from_score_matrix(
        match_id="m-1",
        home_team="A",
        away_team="B",
        expected_home_goals=1.2,
        expected_away_goals=0.8,
        score_matrix=[[0.25, 0.15], [0.20, 0.40]],
        data_version="data-v1",
        model_version="model-v1",
    )

    assert prediction.outcomes.home == pytest.approx(0.20)
    assert prediction.outcomes.draw == pytest.approx(0.65)
    assert prediction.outcomes.away == pytest.approx(0.15)
    assert sum(sum(row) for row in prediction.score_matrix) == pytest.approx(1.0)


def test_outcome_probabilities_reject_invalid_sum() -> None:
    with pytest.raises(ValidationError, match="sum to 1"):
        OutcomeProbabilities(home=0.7, draw=0.3, away=0.2)
