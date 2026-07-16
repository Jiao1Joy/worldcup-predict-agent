import pytest

from worldcup_agent.prediction.metrics import ranked_probability_score, select_goal_model


def test_rps_rewards_probability_on_observed_result() -> None:
    good = ranked_probability_score([0.8, 0.15, 0.05], outcome_index=0)
    bad = ranked_probability_score([0.05, 0.15, 0.8], outcome_index=0)
    assert good < bad


def test_bivariate_wins_within_epsilon() -> None:
    scores = {"poisson": 0.19, "bivariate_poisson": 0.181, "dixon_coles": 0.1805}
    assert select_goal_model(scores, epsilon=0.001) == "bivariate_poisson"


def test_intensities_are_symmetric_at_equal_elo() -> None:
    from worldcup_agent.prediction.features import elo_goal_intensities
    home, away = elo_goal_intensities(1500, 1500, neutral=True, mu=0.2, xi=0.001)
    assert home == pytest.approx(away)
