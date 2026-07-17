# Prediction Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a leakage-safe, versioned prediction engine that produces calibrated match score matrices, outcome probabilities, model artifacts, and a reproducible 2022 backtest.

**Architecture:** The engine is a pure Python domain package beneath the Agent layer. A snapshot pipeline normalizes historical internationals; Elo and three goal models produce priors, a baseline ML calibrator corrects them, and versioned manifests make every runtime prediction reproducible.

**Tech Stack:** Python 3.11, Pydantic 2, pandas, NumPy, SciPy, scikit-learn, joblib, PyArrow, pytest

---

## Dependency

Complete `docs/superpowers/plans/2026-07-15-agent-runtime-foundation.md` first so `backend/pyproject.toml`, the Python package, and the temporary demo fixture exist. Later plans replace the product path while retaining demo tools only for isolated tests and offline failure scenarios.

## File Structure

```text
backend/
├── pyproject.toml
├── src/worldcup_agent/
│   ├── data/
│   │   ├── aliases.py
│   │   ├── contracts.py
│   │   ├── normalize.py
│   │   └── snapshot.py
│   ├── prediction/
│   │   ├── contracts.py
│   │   ├── elo.py
│   │   ├── goal_models.py
│   │   ├── metrics.py
│   │   ├── features.py
│   │   ├── calibration.py
│   │   ├── ensemble.py
│   │   └── service.py
│   ├── artifacts/
│   │   ├── manifest.py
│   │   └── repository.py
│   ├── backtest/
│   │   ├── evaluator.py
│   │   └── report.py
│   └── cli/
│       └── rebuild.py
└── tests/
    ├── fixtures/international_results_small.csv
    ├── unit/data/
    ├── unit/prediction/
    ├── integration/test_artifact_roundtrip.py
    └── integration/test_2022_backtest.py
```

## Task 1: Add Prediction Dependencies and Stable Contracts

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/src/worldcup_agent/data/contracts.py`
- Create: `backend/src/worldcup_agent/prediction/contracts.py`
- Test: `backend/tests/unit/prediction/test_contracts.py`

- [ ] **Step 1: Write failing probability-contract tests**

```python
# backend/tests/unit/prediction/test_contracts.py
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/prediction/test_contracts.py -v`

Expected: FAIL because prediction contracts do not exist.

- [ ] **Step 3: Extend package dependencies**

Add these entries to `[project].dependencies` without removing the existing Agent Runtime dependencies:

```toml
"joblib>=1.4,<2",
"numpy>=2.1,<3",
"pandas>=2.2,<3",
"pyarrow>=18,<20",
"scikit-learn>=1.6,<2",
"scipy>=1.14,<2",
```

Add an optional training profile:

```toml
[project.optional-dependencies]
dev = [
  "httpx>=0.28,<1",
  "pytest>=8.3,<9",
  "pytest-asyncio>=0.25,<1",
  "ruff>=0.9,<1",
]
full-training = [
  "catboost>=1.2,<2",
  "lightgbm>=4.5,<5",
  "xgboost>=2.1,<3",
]
```

- [ ] **Step 4: Implement immutable contracts**

```python
# backend/src/worldcup_agent/data/contracts.py
from datetime import UTC, date, datetime

from pydantic import BaseModel, Field


class HistoricalMatch(BaseModel):
    match_id: str
    date: date
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
```

```python
# backend/src/worldcup_agent/prediction/contracts.py
from pydantic import BaseModel, Field, model_validator


class OutcomeProbabilities(BaseModel):
    home: float = Field(ge=0, le=1)
    draw: float = Field(ge=0, le=1)
    away: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def normalized(self):
        if abs(self.home + self.draw + self.away - 1.0) > 1e-9:
            raise ValueError("outcome probabilities must sum to 1")
        return self


class MatchPrediction(BaseModel):
    match_id: str
    home_team: str
    away_team: str
    expected_home_goals: float = Field(ge=0)
    expected_away_goals: float = Field(ge=0)
    outcomes: OutcomeProbabilities
    score_matrix: list[list[float]]
    data_version: str
    model_version: str
    evidence_ids: list[str] = Field(default_factory=list)

    @classmethod
    def from_score_matrix(cls, **values):
        matrix = values.pop("score_matrix")
        total = sum(sum(row) for row in matrix)
        if total <= 0:
            raise ValueError("score matrix must contain positive probability")
        normalized = [[cell / total for cell in row] for row in matrix]
        home = sum(cell for i, row in enumerate(normalized) for j, cell in enumerate(row) if i > j)
        draw = sum(row[i] for i, row in enumerate(normalized) if i < len(row))
        away = 1.0 - home - draw
        return cls(
            **values,
            score_matrix=normalized,
            outcomes=OutcomeProbabilities(home=home, draw=draw, away=away),
        )
```

- [ ] **Step 5: Run contract tests and static checks**

Run: `cd backend && python -m pytest tests/unit/prediction/test_contracts.py -v && python -m ruff check src tests`

Expected: tests PASS and Ruff reports no errors.

- [ ] **Step 6: Commit contracts**

```bash
git add backend/pyproject.toml backend/src/worldcup_agent/data backend/src/worldcup_agent/prediction/contracts.py backend/tests/unit/prediction/test_contracts.py
git commit -m "feat: define prediction engine contracts"
```

## Task 2: Normalize Historical Matches and Build Leakage-Safe Snapshots

**Files:**
- Create: `backend/src/worldcup_agent/data/aliases.py`
- Create: `backend/src/worldcup_agent/data/normalize.py`
- Create: `backend/src/worldcup_agent/data/snapshot.py`
- Test: `backend/tests/unit/data/test_snapshot.py`

- [ ] **Step 1: Write failing cutoff, alias, and hash tests**

```python
# backend/tests/unit/data/test_snapshot.py
from datetime import UTC, datetime

import pandas as pd

from worldcup_agent.data.snapshot import build_snapshot


def test_snapshot_normalizes_aliases_and_excludes_future_rows(tmp_path) -> None:
    source = tmp_path / "results.csv"
    pd.DataFrame(
        [
            {"date": "2022-11-18", "home_team": "USA", "away_team": "IR Iran", "home_score": 1, "away_score": 0, "tournament": "Friendly", "city": "A", "country": "B", "neutral": True},
            {"date": "2022-11-21", "home_team": "United States", "away_team": "Iran", "home_score": 2, "away_score": 0, "tournament": "World Cup", "city": "C", "country": "D", "neutral": True},
        ]
    ).to_csv(source, index=False)

    frame, manifest = build_snapshot(
        source,
        tmp_path / "snapshot.parquet",
        cutoff=datetime(2022, 11, 19, 23, 59, 59, tzinfo=UTC),
        source_uri="fixture://results.csv",
    )

    assert len(frame) == 1
    assert frame.iloc[0]["home_team"] == "United States"
    assert frame.iloc[0]["away_team"] == "Iran"
    assert manifest.row_count == 1
    assert len(manifest.source_sha256) == 64
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && python -m pytest tests/unit/data/test_snapshot.py -v`

Expected: FAIL because snapshot modules do not exist.

- [ ] **Step 3: Implement aliases and normalization**

```python
# backend/src/worldcup_agent/data/aliases.py
TEAM_ALIASES = {
    "USA": "United States",
    "USMNT": "United States",
    "IR Iran": "Iran",
    "Korea Republic": "South Korea",
    "Côte d'Ivoire": "Ivory Coast",
}
```

```python
# backend/src/worldcup_agent/data/normalize.py
import pandas as pd

from worldcup_agent.data.aliases import TEAM_ALIASES

REQUIRED_COLUMNS = {
    "date", "home_team", "away_team", "home_score", "away_score",
    "tournament", "city", "country", "neutral",
}


def normalize_matches(frame: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"missing match columns: {sorted(missing)}")
    result = frame.copy()
    result["date"] = pd.to_datetime(result["date"], utc=True)
    for column in ("home_team", "away_team"):
        result[column] = result[column].str.strip().replace(TEAM_ALIASES)
    result["home_score"] = result["home_score"].astype("int64")
    result["away_score"] = result["away_score"].astype("int64")
    result["neutral"] = result["neutral"].astype("bool")
    result = result.sort_values(["date", "home_team", "away_team"]).drop_duplicates(
        ["date", "home_team", "away_team", "home_score", "away_score", "tournament"]
    )
    result["match_id"] = [f"INT-{index:06d}" for index in range(1, len(result) + 1)]
    return result.reset_index(drop=True)
```

- [ ] **Step 4: Implement immutable snapshot output**

```python
# backend/src/worldcup_agent/data/snapshot.py
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from worldcup_agent.data.contracts import DataSnapshotManifest
from worldcup_agent.data.normalize import normalize_matches


def build_snapshot(source: Path, output: Path, cutoff: datetime, source_uri: str):
    source_bytes = source.read_bytes()
    frame = normalize_matches(pd.read_csv(source))
    frame = frame[frame["date"] <= cutoff].copy()
    if frame.empty:
        raise ValueError("snapshot contains no matches before cutoff")
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output, index=False)
    digest = hashlib.sha256(source_bytes).hexdigest()
    manifest = DataSnapshotManifest(
        data_version=f"matches-{cutoff:%Y%m%d}-{digest[:12]}",
        source_name="martj42-international-results",
        source_uri=source_uri,
        source_sha256=digest,
        snapshot_cutoff=cutoff,
        row_count=len(frame),
    )
    output.with_suffix(".manifest.json").write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    return frame, manifest
```

- [ ] **Step 5: Run snapshot tests**

Run: `cd backend && python -m pytest tests/unit/data/test_snapshot.py -v`

Expected: PASS.

- [ ] **Step 6: Commit the snapshot pipeline**

```bash
git add backend/src/worldcup_agent/data backend/tests/unit/data/test_snapshot.py
git commit -m "feat: build leakage safe match snapshots"
```

## Task 3: Implement Pre-Match Weighted Elo

**Files:**
- Create: `backend/src/worldcup_agent/prediction/elo.py`
- Test: `backend/tests/unit/prediction/test_elo.py`

- [ ] **Step 1: Write a failing no-future-information test**

```python
# backend/tests/unit/prediction/test_elo.py
from worldcup_agent.prediction.elo import EloEngine, MatchForElo


def test_elo_snapshot_is_captured_before_match_update() -> None:
    engine = EloEngine()
    before = engine.process(
        MatchForElo(home_team="A", away_team="B", home_score=3, away_score=0, tournament="FIFA World Cup", neutral=True)
    )

    assert before.home_rating == 1500
    assert before.away_rating == 1500
    assert engine.rating("A") > 1500
    assert engine.rating("B") < 1500


def test_neutral_match_has_no_home_adjustment() -> None:
    engine = EloEngine()
    probability = engine.expected_home_score("A", "B", neutral=True)
    assert probability == 0.5
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && python -m pytest tests/unit/prediction/test_elo.py -v`

Expected: FAIL because `EloEngine` does not exist.

- [ ] **Step 3: Implement weighted Elo**

```python
# backend/src/worldcup_agent/prediction/elo.py
from dataclasses import dataclass


@dataclass(frozen=True)
class MatchForElo:
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    tournament: str
    neutral: bool


@dataclass(frozen=True)
class PreMatchElo:
    home_rating: float
    away_rating: float
    expected_home: float


class EloEngine:
    def __init__(self, initial: float = 1500.0, home_advantage: float = 100.0) -> None:
        self.initial = initial
        self.home_advantage = home_advantage
        self._ratings: dict[str, float] = {}

    def rating(self, team: str) -> float:
        return self._ratings.get(team, self.initial)

    def expected_home_score(self, home: str, away: str, neutral: bool) -> float:
        advantage = 0.0 if neutral else self.home_advantage
        difference = self.rating(home) + advantage - self.rating(away)
        return 1.0 / (1.0 + 10 ** (-difference / 400.0))

    def process(self, match: MatchForElo) -> PreMatchElo:
        home_before = self.rating(match.home_team)
        away_before = self.rating(match.away_team)
        expected = self.expected_home_score(match.home_team, match.away_team, match.neutral)
        actual = 1.0 if match.home_score > match.away_score else 0.0 if match.home_score < match.away_score else 0.5
        goal_difference = abs(match.home_score - match.away_score)
        multiplier = 1.0 if goal_difference <= 1 else 1.5 if goal_difference == 2 else (11 + goal_difference) / 8
        k = self._k_factor(match.tournament)
        change = k * multiplier * (actual - expected)
        self._ratings[match.home_team] = home_before + change
        self._ratings[match.away_team] = away_before - change
        return PreMatchElo(home_before, away_before, expected)

    @staticmethod
    def _k_factor(tournament: str) -> float:
        name = tournament.casefold()
        if "world cup" in name and "qualification" not in name:
            return 60.0
        if "qualification" in name or "qualifier" in name:
            return 25.0
        if "friendly" in name:
            return 20.0
        return 35.0
```

- [ ] **Step 4: Run Elo tests**

Run: `cd backend && python -m pytest tests/unit/prediction/test_elo.py -v`

Expected: PASS.

- [ ] **Step 5: Commit Elo**

```bash
git add backend/src/worldcup_agent/prediction/elo.py backend/tests/unit/prediction/test_elo.py
git commit -m "feat: add pre match weighted elo"
```

## Task 4: Implement Three Goal-Probability Models

**Files:**
- Create: `backend/src/worldcup_agent/prediction/goal_models.py`
- Test: `backend/tests/unit/prediction/test_goal_models.py`

- [ ] **Step 1: Write failing normalization and low-score tests**

```python
# backend/tests/unit/prediction/test_goal_models.py
import numpy as np
import pytest

from worldcup_agent.prediction.goal_models import bivariate_poisson_matrix, dixon_coles_matrix, poisson_matrix


@pytest.mark.parametrize(
    ("factory", "args"),
    [
        (poisson_matrix, (1.4, 0.9)),
        (bivariate_poisson_matrix, (1.2, 0.7, 0.2)),
        (dixon_coles_matrix, (1.4, 0.9, -0.08)),
    ],
)
def test_score_matrix_is_non_negative_and_normalized(factory, args) -> None:
    matrix = factory(*args, max_goals=8)
    assert matrix.shape == (9, 9)
    assert np.all(matrix >= 0)
    assert matrix.sum() == pytest.approx(1.0)


def test_dixon_coles_changes_low_score_mass() -> None:
    baseline = poisson_matrix(1.4, 0.9, max_goals=8)
    corrected = dixon_coles_matrix(1.4, 0.9, rho=-0.08, max_goals=8)
    assert corrected[0, 0] != pytest.approx(baseline[0, 0])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && python -m pytest tests/unit/prediction/test_goal_models.py -v`

Expected: FAIL because goal-model functions do not exist.

- [ ] **Step 3: Implement the probability matrices**

```python
# backend/src/worldcup_agent/prediction/goal_models.py
from math import exp, factorial

import numpy as np
from scipy.stats import poisson


def _normalize(matrix: np.ndarray) -> np.ndarray:
    matrix = np.clip(matrix, 0.0, None)
    total = float(matrix.sum())
    if total <= 0:
        raise ValueError("score matrix has no probability mass")
    return matrix / total


def poisson_matrix(home_lambda: float, away_lambda: float, max_goals: int = 8) -> np.ndarray:
    goals = np.arange(max_goals + 1)
    return _normalize(np.outer(poisson.pmf(goals, home_lambda), poisson.pmf(goals, away_lambda)))


def bivariate_poisson_matrix(lambda_home: float, lambda_away: float, shared: float, max_goals: int = 8) -> np.ndarray:
    matrix = np.zeros((max_goals + 1, max_goals + 1), dtype=float)
    base = exp(-(lambda_home + lambda_away + shared))
    for home in range(max_goals + 1):
        for away in range(max_goals + 1):
            matrix[home, away] = base * sum(
                lambda_home ** (home - k) * lambda_away ** (away - k) * shared**k
                / (factorial(home - k) * factorial(away - k) * factorial(k))
                for k in range(min(home, away) + 1)
            )
    return _normalize(matrix)


def dixon_coles_matrix(home_lambda: float, away_lambda: float, rho: float, max_goals: int = 8) -> np.ndarray:
    matrix = poisson_matrix(home_lambda, away_lambda, max_goals)
    factors = {
        (0, 0): 1 - home_lambda * away_lambda * rho,
        (1, 0): 1 + away_lambda * rho,
        (0, 1): 1 + home_lambda * rho,
        (1, 1): 1 - rho,
    }
    for score, factor in factors.items():
        matrix[score] *= factor
    return _normalize(matrix)
```

- [ ] **Step 4: Run goal-model tests**

Run: `cd backend && python -m pytest tests/unit/prediction/test_goal_models.py -v`

Expected: PASS.

- [ ] **Step 5: Commit goal probability models**

```bash
git add backend/src/worldcup_agent/prediction/goal_models.py backend/tests/unit/prediction/test_goal_models.py
git commit -m "feat: add three football score models"
```

## Task 5: Add Metrics, Elo-Driven Intensities, and Model Selection

**Files:**
- Create: `backend/src/worldcup_agent/prediction/metrics.py`
- Create: `backend/src/worldcup_agent/prediction/features.py`
- Modify: `backend/src/worldcup_agent/prediction/goal_models.py`
- Test: `backend/tests/unit/prediction/test_model_selection.py`

- [ ] **Step 1: Write failing RPS and selection tests**

```python
# backend/tests/unit/prediction/test_model_selection.py
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && python -m pytest tests/unit/prediction/test_model_selection.py -v`

Expected: FAIL because metrics and features do not exist.

- [ ] **Step 3: Implement metrics and deterministic selection**

```python
# backend/src/worldcup_agent/prediction/metrics.py
def ranked_probability_score(probabilities: list[float], outcome_index: int) -> float:
    observed = [1.0 if index == outcome_index else 0.0 for index in range(3)]
    return 0.5 * sum(
        (sum(probabilities[: boundary + 1]) - sum(observed[: boundary + 1])) ** 2
        for boundary in range(2)
    )


def select_goal_model(scores: dict[str, float], epsilon: float = 0.001) -> str:
    best = min(scores, key=scores.get)
    if scores["bivariate_poisson"] <= scores["dixon_coles"] + epsilon:
        return "bivariate_poisson"
    return best
```

```python
# backend/src/worldcup_agent/prediction/features.py
from math import exp


def elo_goal_intensities(
    home_elo: float,
    away_elo: float,
    neutral: bool,
    mu: float,
    xi: float,
    home_goal_advantage: float = 0.08,
) -> tuple[float, float]:
    difference = (home_elo - away_elo) / 2.0
    adjustment = 0.0 if neutral else home_goal_advantage
    return exp(mu + xi * difference + adjustment), exp(mu - xi * difference)
```

- [ ] **Step 4: Add fitting functions with bounded optimization**

In `goal_models.py`, add:

```python
from collections.abc import Callable

from pydantic import BaseModel
from scipy.optimize import minimize

from worldcup_agent.prediction.features import elo_goal_intensities


class GoalModelParameters(BaseModel):
    model_name: str
    mu: float
    xi: float
    shared: float = 0.0
    rho: float = 0.0
    objective: float
    converged: bool


def fit_goal_model(
    model_name: str,
    home_elos,
    away_elos,
    neutral_flags,
    home_scores,
    away_scores,
) -> GoalModelParameters:
    factories: dict[str, tuple[Callable[..., np.ndarray], list[tuple[float, float]], list[float]]] = {
        "poisson": (poisson_matrix, [(-2.0, 2.0), (-0.01, 0.01)], [0.2, 0.001]),
        "bivariate_poisson": (bivariate_poisson_matrix, [(-2.0, 2.0), (-0.01, 0.01), (0.0, 2.0)], [0.2, 0.001, 0.1]),
        "dixon_coles": (dixon_coles_matrix, [(-2.0, 2.0), (-0.01, 0.01), (-0.25, 0.25)], [0.2, 0.001, -0.05]),
    }
    factory, bounds, initial = factories[model_name]

    def objective(parameters) -> float:
        mu, xi, *extra = parameters
        loss = 0.0
        for home_elo, away_elo, neutral, home_score, away_score in zip(
            home_elos, away_elos, neutral_flags, home_scores, away_scores, strict=True
        ):
            home_lambda, away_lambda = elo_goal_intensities(home_elo, away_elo, neutral, mu, xi)
            matrix = factory(home_lambda, away_lambda, *extra, max_goals=12)
            probability = matrix[min(home_score, 12), min(away_score, 12)]
            loss -= np.log(max(probability, 1e-12))
        return float(loss)

    result = minimize(objective, initial, bounds=bounds, method="L-BFGS-B")
    if not result.success:
        raise RuntimeError("goal model optimization failed")
    mu, xi, *extra = result.x
    return GoalModelParameters(
        model_name=model_name,
        mu=float(mu),
        xi=float(xi),
        shared=float(extra[0]) if model_name == "bivariate_poisson" else 0.0,
        rho=float(extra[0]) if model_name == "dixon_coles" else 0.0,
        objective=float(result.fun),
        converged=True,
    )


def fit_poisson(*args) -> GoalModelParameters:
    return fit_goal_model("poisson", *args)


def fit_bivariate_poisson(*args) -> GoalModelParameters:
    return fit_goal_model("bivariate_poisson", *args)


def fit_dixon_coles(*args) -> GoalModelParameters:
    return fit_goal_model("dixon_coles", *args)
```

- [ ] **Step 5: Run model-selection tests**

Run: `cd backend && python -m pytest tests/unit/prediction/test_model_selection.py tests/unit/prediction/test_goal_models.py -v`

Expected: all tests PASS.

- [ ] **Step 6: Commit model selection**

```bash
git add backend/src/worldcup_agent/prediction backend/tests/unit/prediction
git commit -m "feat: fit and select goal probability models"
```

## Task 6: Implement Baseline Calibration, Fusion, and Artifact Manifests

**Files:**
- Create: `backend/src/worldcup_agent/prediction/calibration.py`
- Create: `backend/src/worldcup_agent/prediction/ensemble.py`
- Create: `backend/src/worldcup_agent/artifacts/manifest.py`
- Create: `backend/src/worldcup_agent/artifacts/repository.py`
- Test: `backend/tests/integration/test_artifact_roundtrip.py`

- [ ] **Step 1: Write a failing artifact round-trip test**

```python
# backend/tests/integration/test_artifact_roundtrip.py
import numpy as np

from worldcup_agent.artifacts.repository import ArtifactRepository
from worldcup_agent.prediction.calibration import train_baseline_calibrator


def test_trained_calibrator_round_trips_with_manifest(tmp_path) -> None:
    features = np.array([[0.6, 0.2, 0.2], [0.2, 0.5, 0.3], [0.1, 0.2, 0.7]])
    labels = np.array([0, 1, 2])
    model = train_baseline_calibrator(features, labels)
    repository = ArtifactRepository(tmp_path)

    manifest = repository.save_baseline(
        model=model,
        data_version="data-v1",
        selected_goal_model="dixon_coles",
        fusion_weights={"elo": 0.2, "goal": 0.5, "ml": 0.3},
        metrics={"rps": 0.18, "log_loss": 0.92, "brier": 0.21},
    )
    loaded, loaded_manifest = repository.load(manifest.model_version, expected_data_version="data-v1")

    assert loaded.predict_proba(features).shape == (3, 3)
    assert loaded_manifest.files[0].sha256
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && python -m pytest tests/integration/test_artifact_roundtrip.py -v`

Expected: FAIL because calibration and artifact modules do not exist.

- [ ] **Step 3: Implement the baseline calibrator and fusion validation**

```python
# backend/src/worldcup_agent/prediction/calibration.py
from sklearn.linear_model import LogisticRegression


def train_baseline_calibrator(features, labels):
    model = LogisticRegression(max_iter=2000, random_state=20260611)
    return model.fit(features, labels)
```

```python
# backend/src/worldcup_agent/prediction/ensemble.py
import numpy as np


def fuse_probabilities(probability_sets: dict[str, np.ndarray], weights: dict[str, float]) -> np.ndarray:
    if set(probability_sets) != set(weights):
        raise ValueError("probability sources and weights must match")
    if any(weight < 0 for weight in weights.values()) or abs(sum(weights.values()) - 1.0) > 1e-9:
        raise ValueError("fusion weights must be non-negative and sum to 1")
    result = sum(probability_sets[name] * weights[name] for name in weights)
    return result / result.sum(axis=1, keepdims=True)
```

- [ ] **Step 4: Implement manifests with file hashes and mismatch rejection**

`manifest.py` defines `ArtifactFile(path, sha256)` and `ModelArtifactManifest(model_version, data_version, trained_until, validation_window, selected_goal_model, fusion_weights, files, metrics, degraded=False)`. `repository.py` saves the calibrator with `joblib`, hashes it with SHA-256, writes `manifest.json`, verifies every hash on load, and raises `ValueError("artifact data version mismatch")` when the expected and stored data versions differ.

- [ ] **Step 5: Run artifact tests**

Run: `cd backend && python -m pytest tests/integration/test_artifact_roundtrip.py -v`

Expected: PASS.

- [ ] **Step 6: Commit calibration and artifacts**

```bash
git add backend/src/worldcup_agent/prediction backend/src/worldcup_agent/artifacts backend/tests/integration/test_artifact_roundtrip.py
git commit -m "feat: persist calibrated prediction artifacts"
```

## Task 7: Build the Match Prediction Service

**Files:**
- Create: `backend/src/worldcup_agent/prediction/service.py`
- Test: `backend/tests/integration/test_match_prediction_service.py`

- [ ] **Step 1: Write a failing end-to-end match prediction test**

```python
# backend/tests/integration/test_match_prediction_service.py
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && python -m pytest tests/integration/test_match_prediction_service.py -v`

Expected: FAIL because `PredictionService` does not exist.

- [ ] **Step 3: Implement the service pipeline**

`RuntimeModels` contains the selected goal parameters, baseline calibrator, fusion weights, data version, and model version. `PredictionService.predict` must:

1. calculate Elo prior probabilities;
2. calculate Elo-driven expected goals;
3. create the selected 9×9 score matrix;
4. derive goal-model outcome probabilities from that matrix;
5. call the baseline calibrator on pre-match features;
6. fuse Elo, goal, and ML probabilities;
7. adjust the score matrix with iterative proportional fitting so its three outcome regions match the fused probabilities;
8. return `MatchPrediction.from_score_matrix` and Evidence ID `MATCH-{match_id}-PRED`.

The iterative adjustment stops at absolute outcome error `<1e-9` or raises `RuntimeError("score matrix reconciliation did not converge")` after 100 iterations.

- [ ] **Step 4: Run service tests**

Run: `cd backend && python -m pytest tests/integration/test_match_prediction_service.py -v`

Expected: PASS.

- [ ] **Step 5: Commit the prediction service**

```bash
git add backend/src/worldcup_agent/prediction/service.py backend/tests/integration/test_match_prediction_service.py
git commit -m "feat: serve reconciled match probabilities"
```

## Task 8: Generate a Reproducible 2022 Backtest

**Files:**
- Create: `backend/src/worldcup_agent/backtest/evaluator.py`
- Create: `backend/src/worldcup_agent/backtest/report.py`
- Test: `backend/tests/integration/test_2022_backtest.py`

- [ ] **Step 1: Write a failing temporal-boundary test**

```python
# backend/tests/integration/test_2022_backtest.py
from datetime import date

from worldcup_agent.backtest.evaluator import BacktestWindow, split_backtest


def test_2022_world_cup_is_never_in_training_partition(sample_matches) -> None:
    train, evaluation = split_backtest(
        sample_matches,
        BacktestWindow(train_end=date(2022, 11, 19), evaluation_end=date(2022, 12, 18)),
    )
    assert train["date"].max().date() <= date(2022, 11, 19)
    assert evaluation["date"].min().date() == date(2022, 11, 20)
    assert evaluation["date"].max().date() <= date(2022, 12, 18)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && python -m pytest tests/integration/test_2022_backtest.py -v`

Expected: FAIL because backtest modules do not exist.

- [ ] **Step 3: Implement temporal splitting and metrics**

`BacktestWindow` is a frozen dataclass. `split_backtest` uses inclusive UTC dates and rejects overlapping or empty partitions. `evaluate_predictions` returns per-match rows plus aggregate RPS, multiclass Log Loss, multiclass Brier, accuracy, and ten equal-width calibration bins. `report.py` serializes `backtest-2022.json` and `backtest-2022-predictions.csv`; it never accepts aggregate metrics as input without per-match rows.

- [ ] **Step 4: Add a fixture-backed integration run**

Use a committed miniature fixture containing matches before 2022-11-20 and at least six 2022 World Cup evaluation matches. Assert that recomputing aggregate RPS from the exported per-match file exactly matches the JSON report within `1e-12`.

- [ ] **Step 5: Run backtest tests**

Run: `cd backend && python -m pytest tests/integration/test_2022_backtest.py -v`

Expected: PASS.

- [ ] **Step 6: Commit backtesting**

```bash
git add backend/src/worldcup_agent/backtest backend/tests/fixtures backend/tests/integration/test_2022_backtest.py
git commit -m "feat: add reproducible 2022 backtest"
```

## Task 9: Add the Rebuild CLI and Completion Gate

**Files:**
- Create: `backend/src/worldcup_agent/cli/rebuild.py`
- Create: `backend/scripts/rebuild_baseline.ps1`
- Create: `backend/docs/PREDICTION_ENGINE.md`
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: Register a CLI entry point**

```toml
[project.scripts]
worldcup-rebuild = "worldcup_agent.cli.rebuild:main"
```

- [ ] **Step 2: Implement explicit rebuild profiles**

`worldcup-rebuild` accepts `--source`, `--output`, `--forecast-cutoff`, `--train-end`, `--backtest-end`, `--seed`, and `--profile baseline|full`. Baseline trains Elo, all three goal models, and Logistic calibration. Full additionally loads optional GBDT adapters and exits with code 2 plus a clear installation command if `full-training` dependencies are absent.

- [ ] **Step 3: Add the PowerShell wrapper**

```powershell
param(
  [Parameter(Mandatory=$true)][string]$Source,
  [string]$Output = "../artifacts/generated"
)
$ErrorActionPreference = "Stop"
worldcup-rebuild --source $Source --output $Output --forecast-cutoff 2026-06-10T23:59:59Z --train-end 2022-11-19 --backtest-end 2022-12-18 --seed 20260611 --profile baseline
```

- [ ] **Step 4: Document data license, commands, outputs, and leakage boundary**

`PREDICTION_ENGINE.md` must document the expected martj42 CSV schema, source attribution, alias file, cutoff semantics, baseline/full profiles, artifact manifest, 2022 evaluation window, and the rule that post-cutoff results cannot enter a frozen forecast.

- [ ] **Step 5: Run the full prediction completion gate**

Run: `cd backend && python -m pytest tests/unit/data tests/unit/prediction tests/integration/test_artifact_roundtrip.py tests/integration/test_match_prediction_service.py tests/integration/test_2022_backtest.py -q`

Expected: all tests PASS.

Run: `cd backend && python -m ruff check src tests`

Expected: Ruff reports no errors.

- [ ] **Step 6: Commit the rebuild workflow**

```bash
git add backend/pyproject.toml backend/src/worldcup_agent/cli backend/scripts backend/docs/PREDICTION_ENGINE.md
git commit -m "docs: add prediction rebuild workflow"
```

## Prediction Engine Completion Gate

Do not start the tournament plan until all conditions hold:

- normalized snapshot hash is stable across two rebuilds;
- no evaluation match exists in the training partition;
- all three goal-model matrices are normalized and non-negative;
- selected model is derived from per-match 2022 RPS;
- runtime artifacts reject a mismatched data version or file hash;
- match outcome probabilities and score-matrix regions agree within `1e-9`;
- baseline rebuild works without optional GBDT libraries;
- backtest metrics can be recomputed from exported per-match rows.
