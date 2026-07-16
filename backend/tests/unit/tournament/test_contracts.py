import pytest
from pydantic import ValidationError

from worldcup_agent.tournament.contracts import StageProbabilities, TournamentForecast


def test_stage_probabilities_are_monotonic() -> None:
    value = StageProbabilities(r32=0.8, r16=0.6, qf=0.4, sf=0.25, final=0.15, champion=0.08)
    assert value.champion == 0.08


def test_stage_probabilities_reject_non_monotonic_values() -> None:
    with pytest.raises(ValidationError, match="monotonic"):
        StageProbabilities(r32=0.5, r16=0.6, qf=0.4, sf=0.2, final=0.1, champion=0.05)


def test_forecast_requires_104_slots() -> None:
    with pytest.raises(ValidationError, match="104"):
        TournamentForecast.model_validate(
            {"forecast_id": "f", "matches": [], "team_probabilities": {}, "simulation_runs": 10, "seed": 1, "versions": {}}
        )
