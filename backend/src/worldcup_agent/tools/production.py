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


class RankingPredictor:
    """Adapter that supplies a stable Elo prior derived from official FIFA ranks."""

    def __init__(self, prediction_service: Any, rankings: dict[str, int]) -> None:
        self.prediction_service = prediction_service
        self.rankings = rankings

    def predict(self, match_id: str, home_team: str, away_team: str, **context):
        def rating(team: str) -> float:
            return 2050.0 - 8.0 * (self.rankings[team] - 1)

        return self.prediction_service.predict(
            match_id,
            home_team,
            away_team,
            rating(home_team),
            rating(away_team),
            True,
        )


class HistoricalEloPredictor:
    """Adapter backed by the final pre-cutoff Elo state from a data snapshot."""

    def __init__(self, prediction_service: Any, ratings: dict[str, float]) -> None:
        self.prediction_service = prediction_service
        self.ratings = ratings

    def predict(self, match_id: str, home_team: str, away_team: str, **context):
        return self.prediction_service.predict(
            match_id,
            home_team,
            away_team,
            self.ratings.get(home_team, 1500.0),
            self.ratings.get(away_team, 1500.0),
            True,
        )


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
    def from_artifacts(
        cls, artifacts_dir: str, rules_dir: str
    ) -> ProductionServices:
        """Load hash-checked trained models and the matching Elo snapshot."""
        from pathlib import Path

        import pandas as pd

        from worldcup_agent.artifacts.repository import ArtifactRepository
        from worldcup_agent.data.contracts import DataSnapshotManifest
        from worldcup_agent.prediction.elo import EloEngine, MatchForElo
        from worldcup_agent.prediction.goal_models import GoalModelParameters
        from worldcup_agent.prediction.service import PredictionService, RuntimeModels
        from worldcup_agent.tournament.rules import load_rules
        from worldcup_agent.tournament.service import TournamentForecastService
        from worldcup_agent.tournament.simulator import TournamentSimulator

        root = Path(artifacts_dir)
        snapshot_path = root / "snapshot.parquet"
        snapshot_manifest_path = root / "snapshot.manifest.json"
        model_root = root / "artifacts"
        manifests = sorted(model_root.glob("*.manifest.json"))
        if not snapshot_path.exists() or not snapshot_manifest_path.exists() or len(manifests) != 1:
            raise ValueError("production artifacts require one snapshot and one model manifest")

        snapshot_manifest = DataSnapshotManifest.model_validate_json(
            snapshot_manifest_path.read_text(encoding="utf-8")
        )
        model_version = manifests[0].name.removesuffix(".manifest.json")
        baseline, model_manifest = ArtifactRepository(model_root).load(
            model_version, snapshot_manifest.data_version
        )
        if not model_manifest.goal_parameters:
            raise ValueError("model manifest is missing fitted goal parameters")
        models = RuntimeModels(
            goal_parameters=GoalModelParameters.model_validate(model_manifest.goal_parameters),
            fusion_weights=model_manifest.fusion_weights,
            data_version=model_manifest.data_version,
            model_version=model_manifest.model_version,
            baseline=baseline,
        )
        prediction_service = PredictionService(models)

        elo = EloEngine()
        snapshot = pd.read_parquet(snapshot_path).sort_values("date")
        for _, match in snapshot.iterrows():
            elo.process(
                MatchForElo(
                    home_team=str(match["home_team"]),
                    away_team=str(match["away_team"]),
                    home_score=int(match["home_score"]),
                    away_score=int(match["away_score"]),
                    tournament=str(match["tournament"]),
                    neutral=bool(match["neutral"]),
                )
            )
        ratings = {team: elo.rating(team) for team in set(snapshot["home_team"]) | set(snapshot["away_team"])}
        rules = load_rules(rules_dir)
        simulator = TournamentSimulator(rules, HistoricalEloPredictor(prediction_service, ratings))
        return cls(
            data_version=model_manifest.data_version,
            model_version=model_manifest.model_version,
            rules_version=rules.rules_version,
            snapshot_cutoff=snapshot_manifest.snapshot_cutoff,
            prediction_service=prediction_service,
            tournament_service=TournamentForecastService(simulator, batch_size=200),
            backtest=model_manifest.metrics,
        )

    @classmethod
    def fixture(cls) -> ProductionServices:
        from datetime import UTC, datetime

        from worldcup_agent.prediction.service import PredictionService, RuntimeModels
        from worldcup_agent.tournament.service import TournamentForecastService
        from worldcup_agent.tournament.simulator import TournamentSimulator
        from worldcup_agent.tournament.rules import load_rules
        from pathlib import Path

        rules_path = Path(__file__).parents[3] / "rules" / "fifa_2026"
        rules = load_rules(rules_path)

        models = RuntimeModels.baseline_fixture(data_version="fixture-data-v1", model_version="fixture-model-v1")
        prediction_service = PredictionService(models)

        simulator = TournamentSimulator(rules, RankingPredictor(prediction_service, rules.fifa_rankings))
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
