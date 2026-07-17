from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class InspectSnapshotInput(BaseModel):
    expected_data_version: str | None = None


class InspectSnapshotOutput(BaseModel):
    data_version: str
    model_version: str
    rules_version: str
    snapshot_cutoff: datetime
    compatible: bool


class PredictMatchInput(BaseModel):
    match_id: str
    home_team: str
    away_team: str
    home_elo: float = 1500.0
    away_elo: float = 1500.0
    neutral: bool = True


class PredictMatchOutput(BaseModel):
    match_id: str
    home_team: str
    away_team: str
    outcomes: dict[str, float]
    score_matrix: list[list[float]]
    evidence_ids: list[str]


class SimulateTournamentInput(BaseModel):
    runs: int = Field(ge=100, le=100_000)
    seed: int
    as_of: datetime | None = None


class SimulateTournamentOutput(BaseModel):
    forecast_id: str
    matches: list[dict[str, Any]]
    team_probabilities: dict[str, Any]
    probability_delta: float
    evidence_ids: list[str]
    provider: str = "tournament-service"


class LoadBacktestInput(BaseModel):
    pass


class LoadBacktestOutput(BaseModel):
    metrics: dict[str, Any]
    per_match_count: int


class RetrieveEvidenceInput(BaseModel):
    evidence_id: str


class RetrieveEvidenceOutput(BaseModel):
    evidence_id: str
    value: Any
