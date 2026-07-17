import pytest

from worldcup_agent.tournament.service import TournamentForecastService


def test_forecast_probabilities_and_batches_are_reproducible(simulator) -> None:
    service = TournamentForecastService(simulator, batch_size=100)
    first = service.forecast(runs=500, seed=7)
    second = service.forecast(runs=500, seed=7)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert sum(value.champion for value in first.team_probabilities.values()) == pytest.approx(1.0)
    assert first.simulation_runs == 500


def test_forecast_requires_104_matches(simulator) -> None:
    service = TournamentForecastService(simulator, batch_size=100)
    forecast = service.forecast(runs=200, seed=7)
    assert len(forecast.matches) == 104
    assert all(match.prediction is not None for match in forecast.matches)
    modal_champion = max(
        forecast.team_probabilities,
        key=lambda team: forecast.team_probabilities[team].champion,
    )
    final = next(match for match in forecast.matches if match.match_id == "M104")
    assert final.winner == modal_champion
