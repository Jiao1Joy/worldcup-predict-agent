"""Simulate a FIFA 2026 tournament forecast and write versioned artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from worldcup_agent.tournament.rules import load_rules
from worldcup_agent.tournament.service import TournamentForecastService
from worldcup_agent.tournament.simulator import TournamentSimulator


def _build_predictor(rules):
    from math import factorial

    import numpy as np

    from worldcup_agent.prediction.contracts import MatchPrediction

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

    return FixturePredictor()


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulate a tournament forecast")
    parser.add_argument("--rules", type=Path, default=Path("rules/fifa_2026"))
    parser.add_argument("--runs", type=int, default=1000)
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260611)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--as-of", type=str, default=None)
    args = parser.parse_args()

    rules = load_rules(args.rules)
    predictor = _build_predictor(rules)
    simulator = TournamentSimulator(rules, predictor)
    service = TournamentForecastService(simulator, batch_size=args.batch_size)
    forecast = service.forecast(runs=args.runs, seed=args.seed, as_of=args.as_of)

    args.output.mkdir(parents=True, exist_ok=True)
    payload = forecast.model_dump(mode="json")
    (args.output / "forecast.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    matches_payload = [{"match_id": m.match_id, "stage": m.stage,
                        "home_team": m.home_team, "away_team": m.away_team,
                        "winner": m.winner} for m in forecast.matches]
    (args.output / "matches.json").write_text(
        json.dumps(matches_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    teams_payload = {team: probs.model_dump() for team, probs in forecast.team_probabilities.items()}
    (args.output / "teams.json").write_text(
        json.dumps(teams_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.output / "evidence.json").write_text(
        json.dumps([{"evidence_id": eid, "kind": "forecast"} for eid in forecast.evidence_ids],
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote forecast {forecast.forecast_id} ({args.runs} runs) to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
