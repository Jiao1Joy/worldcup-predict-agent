from math import factorial
from pathlib import Path

import numpy as np
import pytest

from worldcup_agent.prediction.contracts import MatchPrediction
from worldcup_agent.tournament.rules import load_rules


@pytest.fixture
def sqlite_path(tmp_path: Path) -> Path:
    return tmp_path / "agent-test.sqlite3"


@pytest.fixture
def rules_dir() -> Path:
    return Path(__file__).parents[1] / "rules" / "fifa_2026"


@pytest.fixture
def rules(rules_dir):
    return load_rules(rules_dir)


@pytest.fixture
def deterministic_predictor():
    class DeterministicPredictor:
        def predict(self, match_id: str, home_team: str, away_team: str, **context) -> MatchPrediction:
            # Deterministic strength derived from team name hash; stable across runs.
            home_strength = (sum(ord(c) for c in home_team) % 100) / 100.0
            away_strength = (sum(ord(c) for c in away_team) % 100) / 100.0
            home_lambda = max(0.3, 0.8 + (home_strength - away_strength) * 1.5)
            away_lambda = max(0.3, 0.8 - (home_strength - away_strength) * 1.5)
            goals = np.arange(9)
            home_pois = np.exp(-home_lambda) * home_lambda**goals / np.array(
                [factorial(g) for g in goals]
            )
            away_pois = np.exp(-away_lambda) * away_lambda**goals / np.array(
                [factorial(g) for g in goals]
            )
            matrix = np.outer(home_pois, away_pois)
            matrix = matrix / matrix.sum()
            return MatchPrediction.from_score_matrix(
                match_id=match_id,
                home_team=home_team,
                away_team=away_team,
                expected_home_goals=float(home_lambda),
                expected_away_goals=float(away_lambda),
                score_matrix=matrix.tolist(),
                data_version="fixture-data-v1",
                model_version="fixture-model-v1",
                evidence_ids=[f"MATCH-{match_id}-PRED"],
            )

    return DeterministicPredictor()


@pytest.fixture
def simulator(rules, deterministic_predictor):
    from worldcup_agent.tournament.simulator import TournamentSimulator

    return TournamentSimulator(rules, deterministic_predictor)


@pytest.fixture
def fake_provider():
    class FakeProvider:
        def __init__(self) -> None:
            self.responses: list = []

        def queue(self, value) -> None:
            self.responses.append(value)

        async def complete_structured(self, request, response_model):
            from worldcup_agent.llm.contracts import LLMUsage, StructuredResponse

            value = self.responses.pop(0)
            if isinstance(value, Exception):
                raise value
            return StructuredResponse(value=value, provider="fake", model="fake-model", usage=LLMUsage())

    fake = FakeProvider()
    from worldcup_agent.agent.planner import TaskSpec

    fake.queue(TaskSpec(intent="predict_tournament", mode="portfolio_frozen"))
    return fake


@pytest.fixture
async def runtime_store(tmp_path):
    from worldcup_agent.storage.sqlite import SQLiteRunStore

    store = SQLiteRunStore(tmp_path / "runtime.sqlite3")
    await store.initialize()
    return store


@pytest.fixture
def production_registry():
    from worldcup_agent.tools.production import ProductionServices, build_production_registry

    return build_production_registry(ProductionServices.fixture())


@pytest.fixture
def fallback_planner():
    from worldcup_agent.agent.planner import AgentPlanner

    return AgentPlanner(provider=None)
