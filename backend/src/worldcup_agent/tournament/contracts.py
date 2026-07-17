from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field, model_validator

from worldcup_agent.prediction.contracts import MatchPrediction


class TeamEntry(BaseModel):
    team_id: str
    name: str
    group: str = Field(pattern=r"^[A-L]$")
    fifa_ranking: int = Field(ge=1)


class MatchSlot(BaseModel):
    match_id: str
    stage: str
    home_source: str
    away_source: str
    home_team: str | None = None
    away_team: str | None = None
    prediction: MatchPrediction | None = None
    winner: str | None = None


class StageProbabilities(BaseModel):
    r32: float = Field(ge=0, le=1)
    r16: float = Field(ge=0, le=1)
    qf: float = Field(ge=0, le=1)
    sf: float = Field(ge=0, le=1)
    final: float = Field(ge=0, le=1)
    champion: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def monotonic(self):
        values = [self.r32, self.r16, self.qf, self.sf, self.final, self.champion]
        if values != sorted(values, reverse=True):
            raise ValueError("stage probabilities must be monotonic")
        return self


class TournamentForecast(BaseModel):
    forecast_id: str
    matches: list[MatchSlot]
    team_probabilities: dict[str, StageProbabilities]
    simulation_runs: int = Field(ge=1)
    seed: int
    versions: dict[str, str]
    evidence_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def complete_schedule(self):
        if len(self.matches) != 104:
            raise ValueError("tournament forecast must contain 104 match slots")
        return self


class MatchPredictor(Protocol):
    def predict(self, match_id: str, home_team: str, away_team: str, **context: Any) -> MatchPrediction: ...
