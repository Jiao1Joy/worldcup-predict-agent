# FIFA 2026 Tournament Simulator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, rule-versioned simulator for the 48-team FIFA World Cup 2026 that produces complete group standings, all 104 match slots, advancement probabilities, and reproducible Monte Carlo forecasts.

**Architecture:** Official rules and fixture slots live in validated data files; pure domain functions rank groups and resolve knockout slots. The simulator consumes only a `MatchPredictor` protocol, runs in checkpointable batches, and publishes a versioned `TournamentForecast` with evidence and invariants.

**Tech Stack:** Python 3.11, Pydantic 2, NumPy, pandas, pytest

---

## Dependency

Complete `docs/superpowers/plans/2026-07-16-prediction-engine.md` and pass its completion gate.

Official rule references:

- `https://www.fifa.com/en/articles/groups-how-teams-qualify-tie-breakers`
- `https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/match-schedule-fixtures-results-teams-stadiums`

Record the retrieval date and SHA-256 of every downloaded rule or schedule artifact. Do not derive the 495 Annexe C rows from assumptions.

## File Structure

```text
backend/
├── rules/fifa_2026/
│   ├── rules-manifest.json
│   ├── groups.json
│   ├── fixtures.json
│   ├── annex_c.csv
│   └── README.md
├── src/worldcup_agent/tournament/
│   ├── contracts.py
│   ├── rules.py
│   ├── group_stage.py
│   ├── annex_c.py
│   ├── knockout.py
│   ├── sampler.py
│   ├── simulator.py
│   ├── convergence.py
│   └── service.py
├── src/worldcup_agent/cli/simulate.py
└── tests/
    ├── fixtures/tournament_48_teams.json
    ├── unit/tournament/
    └── integration/test_full_tournament.py
```

## Task 1: Define Rule and Forecast Contracts

**Files:**
- Create: `backend/src/worldcup_agent/tournament/contracts.py`
- Create: `backend/src/worldcup_agent/tournament/rules.py`
- Test: `backend/tests/unit/tournament/test_contracts.py`

- [ ] **Step 1: Write failing manifest and forecast tests**

```python
# backend/tests/unit/tournament/test_contracts.py
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
        TournamentForecast.model_validate({"forecast_id": "f", "matches": [], "team_probabilities": {}, "simulation_runs": 10, "seed": 1, "versions": {}})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/tournament/test_contracts.py -v`

Expected: FAIL because tournament contracts do not exist.

- [ ] **Step 3: Implement domain contracts**

```python
# backend/src/worldcup_agent/tournament/contracts.py
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
```

- [ ] **Step 4: Define rule manifest validation**

`rules.py` defines `RulesManifest(rules_version, effective_date, source_urls, source_sha256, groups_sha256, fixtures_sha256, annex_c_sha256)` and `load_rules(directory)`. The loader hashes each data file, rejects any mismatch, requires groups A-L with four unique teams each, requires match IDs M001-M104 exactly once, and refuses to start if `annex_c.csv` has anything other than 495 data rows.

- [ ] **Step 5: Run contract tests**

Run: `cd backend && python -m pytest tests/unit/tournament/test_contracts.py -v`

Expected: PASS.

- [ ] **Step 6: Commit tournament contracts**

```bash
git add backend/src/worldcup_agent/tournament backend/tests/unit/tournament/test_contracts.py
git commit -m "feat: define fifa tournament contracts"
```

## Task 2: Implement Group Match Generation and Tie-Breaking

**Files:**
- Create: `backend/src/worldcup_agent/tournament/group_stage.py`
- Test: `backend/tests/unit/tournament/test_group_stage.py`

- [ ] **Step 1: Write failing round-robin and head-to-head tests**

```python
# backend/tests/unit/tournament/test_group_stage.py
from worldcup_agent.tournament.group_stage import GroupResult, create_group_matches, rank_group


def test_four_team_group_contains_six_unique_matches() -> None:
    matches = create_group_matches("A", ["A1", "A2", "A3", "A4"])
    assert len(matches) == 6
    assert len({frozenset((match.home_team, match.away_team)) for match in matches}) == 6


def test_head_to_head_points_break_overall_goal_difference_tie() -> None:
    results = [
        GroupResult("A", "A1", "A2", 1, 0, fair_play_home=0, fair_play_away=0),
        GroupResult("A", "A1", "A3", 0, 3, 0, 0),
        GroupResult("A", "A1", "A4", 2, 0, 0, 0),
        GroupResult("A", "A2", "A3", 2, 0, 0, 0),
        GroupResult("A", "A2", "A4", 2, 0, 0, 0),
        GroupResult("A", "A3", "A4", 0, 4, 0, 0),
    ]
    ranked = rank_group(results, fifa_rankings={"A1": 10, "A2": 20, "A3": 30, "A4": 40})
    assert ranked.index("A1") < ranked.index("A2")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/tournament/test_group_stage.py -v`

Expected: FAIL because group-stage functions do not exist.

- [ ] **Step 3: Implement group standings**

`group_stage.py` must define:

```python
from dataclasses import dataclass
from itertools import combinations


@dataclass(frozen=True)
class ScheduledGroupMatch:
    match_id: str
    group: str
    home_team: str
    away_team: str


@dataclass(frozen=True)
class GroupResult:
    group: str
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    fair_play_home: int
    fair_play_away: int


def create_group_matches(group: str, teams: list[str]) -> list[ScheduledGroupMatch]:
    if len(teams) != 4 or len(set(teams)) != 4:
        raise ValueError("group must contain four unique teams")
    return [
        ScheduledGroupMatch(f"{group}-G{index}", group, home, away)
        for index, (home, away) in enumerate(combinations(teams, 2), start=1)
    ]
```

Add `StandingRow` with played, wins, draws, losses, goals_for, goals_against, points, fair_play. `rank_group` first orders by points. For every tied subset, it builds a mini-table from matches only between tied teams and applies head-to-head points, head-to-head goal difference, and the official head-to-head goals criterion. Still-tied teams then use overall goal difference, overall goals, fair-play score, and ascending FIFA ranking. Reapply the mini-table to the remaining tied subset after any partial split.

- [ ] **Step 4: Add a three-way recursive tie fixture**

Add a test in which three teams are tied, one separates on the mini-table, and the remaining two require a recalculated two-team head-to-head comparison. Assert the exact order and ensure original input results remain unchanged.

- [ ] **Step 5: Run group tests**

Run: `cd backend && python -m pytest tests/unit/tournament/test_group_stage.py -v`

Expected: PASS.

- [ ] **Step 6: Commit group ranking**

```bash
git add backend/src/worldcup_agent/tournament/group_stage.py backend/tests/unit/tournament/test_group_stage.py
git commit -m "feat: implement fifa group tie breakers"
```

## Task 3: Version the Official Groups, Fixtures, and Annexe C Table

**Files:**
- Create: `backend/rules/fifa_2026/rules-manifest.json`
- Create: `backend/rules/fifa_2026/groups.json`
- Create: `backend/rules/fifa_2026/fixtures.json`
- Create: `backend/rules/fifa_2026/annex_c.csv`
- Create: `backend/rules/fifa_2026/README.md`
- Create: `backend/src/worldcup_agent/tournament/annex_c.py`
- Test: `backend/tests/unit/tournament/test_annex_c.py`

- [ ] **Step 1: Write failing coverage tests**

```python
# backend/tests/unit/tournament/test_annex_c.py
from itertools import combinations

from worldcup_agent.tournament.annex_c import AnnexC


def test_annex_c_covers_every_eight_group_combination(rules_dir) -> None:
    table = AnnexC.load(rules_dir / "annex_c.csv")
    expected = {"".join(groups) for groups in combinations("ABCDEFGHIJKL", 8)}
    assert set(table.combinations) == expected
    assert len(table.combinations) == 495


def test_each_mapping_uses_each_qualified_group_once(rules_dir) -> None:
    table = AnnexC.load(rules_dir / "annex_c.csv")
    for combination, slots in table.combinations.items():
        assert sorted(slots.values()) == sorted(combination)
        assert len(slots) == 8
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/tournament/test_annex_c.py -v`

Expected: FAIL because the rule data and loader do not exist.

- [ ] **Step 3: Add official rule data with provenance**

Create `annex_c.csv` with header:

```csv
qualified_groups,slot_1A,slot_1B,slot_1D,slot_1E,slot_1G,slot_1I,slot_1K,slot_1L
```

Populate exactly 495 rows from Annexe C. `qualified_groups` is the sorted eight-letter key. Each slot cell contains one of those eight group letters. `README.md` records the official regulation URL, retrieval date, source page/table, extraction method, reviewer, and file SHA-256. `groups.json` contains 12 groups of four team IDs. `fixtures.json` contains official M001-M104 slot sources, dates, stages, and venues; no Python code may embed these values.

- [ ] **Step 4: Implement a strict loader**

```python
# backend/src/worldcup_agent/tournament/annex_c.py
import csv
from itertools import combinations
from pathlib import Path


class AnnexC:
    SLOT_COLUMNS = ("slot_1A", "slot_1B", "slot_1D", "slot_1E", "slot_1G", "slot_1I", "slot_1K", "slot_1L")

    def __init__(self, combinations_by_key: dict[str, dict[str, str]]) -> None:
        self.combinations = combinations_by_key

    @classmethod
    def load(cls, path: Path):
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        mapping = {
            row["qualified_groups"]: {column.removeprefix("slot_"): row[column] for column in cls.SLOT_COLUMNS}
            for row in rows
        }
        expected = {"".join(value) for value in combinations("ABCDEFGHIJKL", 8)}
        if set(mapping) != expected:
            raise ValueError("Annexe C must cover all 495 combinations")
        for key, slots in mapping.items():
            if sorted(slots.values()) != sorted(key):
                raise ValueError(f"Annexe C mapping is invalid for {key}")
        return cls(mapping)

    def resolve(self, qualified_groups: set[str]) -> dict[str, str]:
        return self.combinations["".join(sorted(qualified_groups))]
```

- [ ] **Step 5: Run rule-data tests and hash validation**

Run: `cd backend && python -m pytest tests/unit/tournament/test_annex_c.py -v`

Expected: PASS with all 495 combinations.

- [ ] **Step 6: Commit official rule data separately**

```bash
git add backend/rules/fifa_2026 backend/src/worldcup_agent/tournament/annex_c.py backend/tests/unit/tournament/test_annex_c.py
git commit -m "data: version fifa 2026 tournament rules"
```

## Task 4: Implement Best-Third Ranking and Knockout Slot Resolution

**Files:**
- Create: `backend/src/worldcup_agent/tournament/knockout.py`
- Modify: `backend/src/worldcup_agent/tournament/group_stage.py`
- Test: `backend/tests/unit/tournament/test_knockout.py`

- [ ] **Step 1: Write failing best-third and bracket tests**

```python
# backend/tests/unit/tournament/test_knockout.py
from worldcup_agent.tournament.knockout import rank_best_thirds, resolve_round_of_32


def test_best_thirds_use_points_goal_difference_goals_fair_play_and_ranking(third_rows) -> None:
    selected = rank_best_thirds(third_rows, fifa_rankings=third_rows.rankings)
    assert len(selected) == 8
    assert [row.team for row in selected] == third_rows.expected_order[:8]


def test_round_of_32_contains_sixteen_unique_matches(group_rankings, annex_c, fixture_slots) -> None:
    matches = resolve_round_of_32(group_rankings, annex_c, fixture_slots)
    assert len(matches) == 16
    teams = [team for match in matches for team in (match.home_team, match.away_team)]
    assert len(teams) == len(set(teams)) == 32
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/tournament/test_knockout.py -v`

Expected: FAIL because knockout resolution does not exist.

- [ ] **Step 3: Implement best-third ordering**

`rank_best_thirds` sorts the 12 third-place `StandingRow` objects by points, overall goal difference, goals scored, fair-play score, and ascending FIFA ranking. It returns exactly eight and raises if fewer or more than 12 group rows are supplied.

- [ ] **Step 4: Resolve official Round-of-32 sources**

`resolve_round_of_32` gets each `1X`, `2X`, and `3X` source from group rankings and the selected Annexe C mapping. It validates that 32 unique teams fill 16 official M073-M088 match slots. `resolve_later_rounds` fills M089-M104 only from `W<match_id>` or `L<semifinal_match_id>` sources in `fixtures.json`; it never guesses pairings by list position.

- [ ] **Step 5: Run knockout tests**

Run: `cd backend && python -m pytest tests/unit/tournament/test_knockout.py -v`

Expected: PASS.

- [ ] **Step 6: Commit knockout resolution**

```bash
git add backend/src/worldcup_agent/tournament backend/tests/unit/tournament/test_knockout.py
git commit -m "feat: resolve fifa knockout slots"
```

## Task 5: Sample Group and Knockout Matches Consistently

**Files:**
- Create: `backend/src/worldcup_agent/tournament/sampler.py`
- Test: `backend/tests/unit/tournament/test_sampler.py`

- [ ] **Step 1: Write failing deterministic sampling tests**

```python
# backend/tests/unit/tournament/test_sampler.py
import numpy as np

from worldcup_agent.tournament.sampler import sample_group_score, sample_knockout_winner


def test_group_score_uses_score_matrix() -> None:
    matrix = np.zeros((3, 3)); matrix[2, 1] = 1.0
    assert sample_group_score(matrix, np.random.default_rng(7)) == (2, 1)


def test_knockout_draw_reaches_extra_time_and_penalties() -> None:
    matrix = np.zeros((2, 2)); matrix[0, 0] = 1.0
    result = sample_knockout_winner("A", "B", matrix, np.random.default_rng(7), penalty_home_probability=0.5)
    assert result.winner in {"A", "B"}
    assert result.decided_by in {"extra_time", "penalties"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/tournament/test_sampler.py -v`

Expected: FAIL because sampler functions do not exist.

- [ ] **Step 3: Implement sampling without outcome overrides**

Flatten the normalized score matrix and sample one index with `Generator.choice`. Convert the index back to `(home_goals, away_goals)`. Knockout draws sample extra-time goals from Poisson rates equal to one third of the regulation expected goals. If still tied, sample penalties from `penalty_home_probability`, default 0.5. Never replace a sampled draw with the higher-Elo team.

- [ ] **Step 4: Add a 10,000-sample frequency test**

For a fixed 2×2 matrix, sample 10,000 scores and assert each empirical cell is within 0.02 of its configured probability. Use a fixed RNG seed so the test is deterministic.

- [ ] **Step 5: Run sampler tests**

Run: `cd backend && python -m pytest tests/unit/tournament/test_sampler.py -v`

Expected: PASS.

- [ ] **Step 6: Commit match sampling**

```bash
git add backend/src/worldcup_agent/tournament/sampler.py backend/tests/unit/tournament/test_sampler.py
git commit -m "feat: sample regulation and knockout scores"
```

## Task 6: Implement One Complete Tournament Run

**Files:**
- Create: `backend/src/worldcup_agent/tournament/simulator.py`
- Test: `backend/tests/integration/test_full_tournament.py`

- [ ] **Step 1: Write a failing 104-match invariant test**

```python
# backend/tests/integration/test_full_tournament.py
from worldcup_agent.tournament.simulator import TournamentSimulator


def test_one_run_plays_all_104_matches_and_one_champion(rules, deterministic_predictor) -> None:
    simulator = TournamentSimulator(rules, deterministic_predictor)
    result = simulator.run_once(seed=20260611)

    assert len(result.matches) == 104
    assert len([match for match in result.matches if match.stage == "group"]) == 72
    assert len([match for match in result.matches if match.stage == "round_of_32"]) == 16
    assert result.champion in rules.team_ids
    assert all(match.winner for match in result.matches if match.stage != "group")


def test_fixed_seed_produces_identical_run_hash(rules, deterministic_predictor) -> None:
    simulator = TournamentSimulator(rules, deterministic_predictor)
    assert simulator.run_once(7).content_hash == simulator.run_once(7).content_hash
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/integration/test_full_tournament.py -v`

Expected: FAIL because `TournamentSimulator` does not exist.

- [ ] **Step 3: Implement the full run in schedule order**

`TournamentSimulator.run_once` uses one NumPy `Generator` created from the seed. It predicts and samples M001-M072, ranks all groups, selects best thirds, applies Annexe C, resolves M073-M088, then resolves and samples M089-M104 from official winner/loser sources. It returns immutable match results, group tables, qualified thirds, champion, and a SHA-256 of canonical JSON.

- [ ] **Step 4: Add failure assertions for incomplete rules**

Test missing match slot, duplicated team, missing Annexe C combination, unresolved winner source, and probability matrix with invalid sum. Each must fail before returning any partial published forecast.

- [ ] **Step 5: Run full-run tests**

Run: `cd backend && python -m pytest tests/integration/test_full_tournament.py -v`

Expected: PASS.

- [ ] **Step 6: Commit the full simulator**

```bash
git add backend/src/worldcup_agent/tournament/simulator.py backend/tests/integration/test_full_tournament.py
git commit -m "feat: simulate the complete fifa tournament"
```

## Task 7: Add Batched Monte Carlo, Convergence, and Forecast Aggregation

**Files:**
- Create: `backend/src/worldcup_agent/tournament/convergence.py`
- Create: `backend/src/worldcup_agent/tournament/service.py`
- Test: `backend/tests/integration/test_tournament_forecast.py`

- [ ] **Step 1: Write failing aggregation tests**

```python
# backend/tests/integration/test_tournament_forecast.py
import pytest

from worldcup_agent.tournament.service import TournamentForecastService


def test_forecast_probabilities_and_batches_are_reproducible(simulator) -> None:
    service = TournamentForecastService(simulator, batch_size=100)
    first = service.forecast(runs=500, seed=7)
    second = service.forecast(runs=500, seed=7)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert sum(value.champion for value in first.team_probabilities.values()) == pytest.approx(1.0)
    assert first.simulation_runs == 500
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/integration/test_tournament_forecast.py -v`

Expected: FAIL because forecast aggregation does not exist.

- [ ] **Step 3: Implement deterministic batch seeds**

For batch index `i`, derive the seed with `numpy.random.SeedSequence([root_seed, i])`. Persist `BatchResult(batch_index, seed_entropy, runs, stage_counts, champion_counts, content_hash)`. Merging batches sorts by batch index and adds integer counts before dividing by total runs; parallel completion order must not change output.

- [ ] **Step 4: Implement convergence records**

After every batch record the maximum absolute change in any champion probability. `is_converged` requires at least 10,000 runs and three consecutive batch deltas below 0.005. It is advisory: explicit `runs` always completes exactly that many runs; Agent policy may request more using the convergence record.

- [ ] **Step 5: Run forecast tests**

Run: `cd backend && python -m pytest tests/integration/test_tournament_forecast.py -v`

Expected: PASS.

- [ ] **Step 6: Commit Monte Carlo aggregation**

```bash
git add backend/src/worldcup_agent/tournament backend/tests/integration/test_tournament_forecast.py
git commit -m "feat: aggregate checkpointable tournament forecasts"
```

## Task 8: Add CLI, Evidence, and Tournament Completion Gate

**Files:**
- Create: `backend/src/worldcup_agent/cli/simulate.py`
- Create: `backend/docs/TOURNAMENT_RULES.md`
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: Register the simulator CLI**

```toml
[project.scripts]
worldcup-rebuild = "worldcup_agent.cli.rebuild:main"
worldcup-simulate = "worldcup_agent.cli.simulate:main"
```

- [ ] **Step 2: Implement CLI arguments and output**

`worldcup-simulate` accepts `--rules`, `--artifacts`, `--runs`, `--batch-size`, `--seed`, `--output`, and optional `--as-of`. It validates rule and artifact hashes before simulation, writes `forecast.json`, `matches.json`, `teams.json`, `convergence.json`, and `evidence.json`, and exits non-zero without partial files if an invariant fails.

- [ ] **Step 3: Generate Evidence IDs**

Create `RULE-FIFA26-{rules_version}`, `SIM-{forecast_id}-{batch_index}`, `FORECAST-{forecast_id}`, and one `MATCH-{match_id}-PRED` per predicted match. The published forecast lists all IDs and exact version metadata.

- [ ] **Step 4: Document rule provenance and manual verification**

`TOURNAMENT_RULES.md` explains group criteria, best-third criteria, Annexe C schema, fixture source syntax, 104-match count, extra-time/penalty policy, version/hash checks, and the process for comparing a sample of rows against the FIFA source.

- [ ] **Step 5: Run the completion gate**

Run: `cd backend && python -m pytest tests/unit/tournament tests/integration/test_full_tournament.py tests/integration/test_tournament_forecast.py -q`

Expected: all tests PASS, including 495/495 Annexe C coverage.

Run: `cd backend && python -m ruff check src tests`

Expected: Ruff reports no errors.

- [ ] **Step 6: Commit CLI and documentation**

```bash
git add backend/pyproject.toml backend/src/worldcup_agent/cli/simulate.py backend/docs/TOURNAMENT_RULES.md
git commit -m "docs: add tournament simulation workflow"
```

## Tournament Completion Gate

Do not integrate Agent tools until:

- rule manifest hashes validate;
- groups contain 48 unique teams;
- official fixtures contain M001-M104 exactly once;
- Annexe C covers 495/495 combinations and every row uses its eight groups once;
- all recursive group tie fixtures pass;
- best-third ranking returns exactly eight teams;
- every run contains 72 group and 32 knockout matches;
- one and only one champion exists;
- fixed artifacts and seed produce an identical canonical hash;
- champion probabilities sum to 1 within floating-point tolerance;
- no outcome is overridden after score sampling.
