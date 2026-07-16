from datetime import UTC, datetime

from pydantic import BaseModel, Field


class HistoricalMatch(BaseModel):
    match_id: str
    date: datetime
    home_team: str
    away_team: str
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)
    tournament: str
    city: str = ""
    country: str = ""
    neutral: bool


class DataSnapshotManifest(BaseModel):
    data_version: str
    source_name: str
    source_uri: str
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    snapshot_cutoff: datetime
    row_count: int = Field(ge=1)
    schema_version: str = "match-v1"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
