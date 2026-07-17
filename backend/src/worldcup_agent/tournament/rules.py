from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, Field


class RulesManifest(BaseModel):
    rules_version: str
    effective_date: str
    source_urls: list[str]
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    groups_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    fixtures_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    annex_c_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    fifa_rankings_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    retrieved_at: str = ""


class TournamentRules:
    def __init__(
        self,
        manifest: RulesManifest,
        groups: dict[str, list[str]],
        fixtures: list[dict],
        annex_c_path: Path,
        fifa_rankings: dict[str, int],
    ) -> None:
        self.manifest = manifest
        self.groups = groups
        self.fixtures = fixtures
        self.annex_c_path = annex_c_path
        self.fifa_rankings = fifa_rankings
        self.team_ids = [team for teams in groups.values() for team in teams]
        self.fixtures_by_id = {f["match_id"]: f for f in fixtures}

    @property
    def rules_version(self) -> str:
        return self.manifest.rules_version


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_rules(directory: str | Path) -> TournamentRules:
    root = Path(directory)
    manifest_path = root / "rules-manifest.json"
    manifest = RulesManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))

    groups_path = root / "groups.json"
    fixtures_path = root / "fixtures.json"
    annex_c_path = root / "annex_c.csv"
    fifa_rankings_path = root / "fifa_rankings.json"

    groups_sha = _sha256(groups_path)
    fixtures_sha = _sha256(fixtures_path)
    annex_c_sha = _sha256(annex_c_path)
    fifa_rankings_sha = _sha256(fifa_rankings_path)

    if groups_sha != manifest.groups_sha256:
        raise ValueError("groups.json hash mismatch")
    if fixtures_sha != manifest.fixtures_sha256:
        raise ValueError("fixtures.json hash mismatch")
    if annex_c_sha != manifest.annex_c_sha256:
        raise ValueError("annex_c.csv hash mismatch")
    if fifa_rankings_sha != manifest.fifa_rankings_sha256:
        raise ValueError("fifa_rankings.json hash mismatch")

    groups_data = json.loads(groups_path.read_text(encoding="utf-8"))
    if sorted(groups_data) != list("ABCDEFGHIJKL"):
        raise ValueError("groups must cover A-L")
    team_ids = [team for teams in groups_data.values() for team in teams]
    if len(team_ids) != 48 or len(set(team_ids)) != 48:
        raise ValueError("groups must contain 48 unique teams")

    rankings_data = json.loads(fifa_rankings_path.read_text(encoding="utf-8"))["rankings"]
    if set(rankings_data) != set(team_ids):
        raise ValueError("FIFA rankings must cover exactly the 48 tournament teams")
    if any(not isinstance(rank, int) or rank < 1 for rank in rankings_data.values()):
        raise ValueError("FIFA rankings must be positive integers")

    fixtures_data = json.loads(fixtures_path.read_text(encoding="utf-8"))["matches"]
    match_ids = [f["match_id"] for f in fixtures_data]
    expected = [f"M{i:03d}" for i in range(1, 105)]
    if match_ids != expected:
        raise ValueError("fixtures must be M001-M104 in order")

    return TournamentRules(manifest, groups_data, fixtures_data, annex_c_path, rankings_data)
