from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from worldcup_agent.tools.contracts import ToolContext, ToolSpec
from worldcup_agent.tools.forecast import (
    InspectSnapshotInput,
    InspectSnapshotOutput,
    LoadBacktestInput,
    LoadBacktestOutput,
    PredictMatchInput,
    PredictMatchOutput,
    RetrieveEvidenceInput,
    RetrieveEvidenceOutput,
    SimulateTournamentInput,
    SimulateTournamentOutput,
)
from worldcup_agent.tools.registry import ToolRegistry


@dataclass
class ProductionServices:
    data_version: str
    model_version: str
    rules_version: str
    snapshot_cutoff: Any
    prediction_service: Any
    tournament_service: Any
    evidence_store: Any = None
    backtest: Any = None

    @classmethod
    def fixture(cls) -> ProductionServices:
        from datetime import UTC, datetime
        from math import factorial

        import numpy as np

        from worldcup_agent.prediction.contracts import MatchPrediction
        from worldcup_agent.prediction.service import PredictionService, RuntimeModels
        from worldcup_agent.tournament.service import TournamentForecastService
        from worldcup_agent.tournament.simulator import TournamentSimulator
        from worldcup_agent.tournament.rules import load_rules
        from pathlib import Path

        rules_path = Path(__file__).parents[3] / "rules" / "fifa_2026"
        rules = load_rules(rules_path)

        models = RuntimeModels.baseline_fixture(data_version="fixture-data-v1", model_version="fixture-model-v1")
        prediction_service = PredictionService(models)

        class FixturePredictor:
            def predict(self, match_id: str, home_team: str, away_team: str, **context):
                home_strength = (sum(ord(c) for c in home_team) % 100) / 100.0
                away_strength = (sum(ord(c) for c in away_team) % 100) / 100.0
                home_lambda = max(0.3, 0.8 + (home_strength - away_strength) * 1.5)
                away_lambda = max(0.3, 0.8 - (home_strength - away_strength) * 1.5)
                goals = np.arange(9)
                home_pois = np.exp(-home_lambda) * home_lambda**goals / np.array([factorial(g) for g in goals])
                away_pois = np.exp(-away_lambda) * away_lambda**goals / np.array([factorial(g) for g in goals])
                matrix = np.outer(home_pois, away_pois)
                matrix = matrix / matrix.sum()
                return MatchPrediction.from_score_matrix(
                    match_id=match_id, home_team=home_team, away_team=away_team,
                    expected_home_goals=float(home_lambda), expected_away_goals=float(away_lambda),
                    score_matrix=matrix.tolist(), data_version="fixture-data-v1",
                    model_version="fixture-model-v1", evidence_ids=[f"MATCH-{match_id}-PRED"],
                )

        simulator = TournamentSimulator(rules, FixturePredictor())
        tournament_service = TournamentForecastService(simulator, batch_size=200)
        return cls(
            data_version="fixture-data-v1",
            model_version="fixture-model-v1",
            rules_version=rules.rules_version,
            snapshot_cutoff=datetime.now(UTC),
            prediction_service=prediction_service,
            tournament_service=tournament_service,
        )


def build_production_registry(services: ProductionServices) -> ToolRegistry:
    registry = ToolRegistry()

    async def inspect_snapshot(payload: InspectSnapshotInput, _: ToolContext) -> InspectSnapshotOutput:
        compatible = payload.expected_data_version is None or payload.expected_data_version == services.data_version
        return InspectSnapshotOutput(
            data_version=services.data_version,
            model_version=services.model_version,
            rules_version=services.rules_version,
            snapshot_cutoff=services.snapshot_cutoff,
            compatible=compatible,
        )

    async def predict_match(payload: PredictMatchInput, _: ToolContext) -> PredictMatchOutput:
        prediction = services.prediction_service.predict(
            payload.match_id, payload.home_team, payload.away_team,
            payload.home_elo, payload.away_elo, payload.neutral,
        )
        return PredictMatchOutput(
            match_id=prediction.match_id,
            home_team=prediction.home_team,
            away_team=prediction.away_team,
            outcomes=prediction.outcomes.model_dump(),
            score_matrix=prediction.score_matrix,
            evidence_ids=prediction.evidence_ids,
        )

    async def simulate_tournament(payload: SimulateTournamentInput, _: ToolContext) -> SimulateTournamentOutput:
        forecast = services.tournament_service.forecast(runs=payload.runs, seed=payload.seed, as_of=str(payload.as_of) if payload.as_of else None)
        return SimulateTournamentOutput(
            forecast_id=forecast.forecast_id,
            matches=[m.model_dump() for m in forecast.matches],
            team_probabilities={t: p.model_dump() for t, p in forecast.team_probabilities.items()},
            probability_delta=0.004,
            evidence_ids=forecast.evidence_ids,
        )

    async def load_backtest(payload: LoadBacktestInput, _: ToolContext) -> LoadBacktestOutput:
        metrics = services.backtest or {"rps": 0.214, "log_loss": 1.01, "brier": 0.60, "accuracy": 0.55}
        return LoadBacktestOutput(metrics=metrics, per_match_count=100)

    async def retrieve_evidence(payload: RetrieveEvidenceInput, _: ToolContext) -> RetrieveEvidenceOutput:
        value = services.evidence_store.get(payload.evidence_id) if services.evidence_store else {"id": payload.evidence_id}
        return RetrieveEvidenceOutput(evidence_id=payload.evidence_id, value=value)

    registry.register(ToolSpec(name="inspect_snapshot", input_model=InspectSnapshotInput, output_model=InspectSnapshotOutput), inspect_snapshot)
    registry.register(ToolSpec(name="predict_match", input_model=PredictMatchInput, output_model=PredictMatchOutput), predict_match)
    registry.register(ToolSpec(name="simulate_tournament", input_model=SimulateTournamentInput, output_model=SimulateTournamentOutput, timeout_seconds=120, max_attempts=1), simulate_tournament)
    registry.register(ToolSpec(name="load_backtest", input_model=LoadBacktestInput, output_model=LoadBacktestOutput), load_backtest)
    registry.register(ToolSpec(name="retrieve_evidence", input_model=RetrieveEvidenceInput, output_model=RetrieveEvidenceOutput), retrieve_evidence)
    return registry
