"""Generate the deterministic offline portfolio bundle."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path

from worldcup_agent.tournament.rules import load_rules


async def generate(output: Path, runs: int = 500, seed: int = 20260611) -> None:
    from worldcup_agent.tools.production import ProductionServices, build_production_registry

    output.mkdir(parents=True, exist_ok=True)
    rules = load_rules(Path(__file__).parents[3] / "rules" / "fifa_2026")
    services = ProductionServices.fixture()
    services.tournament_service.simulator.rules = rules

    # Run a production Agent run for the completed-run fixture.
    from worldcup_agent.storage.sqlite import SQLiteRunStore

    store = SQLiteRunStore(output / "portfolio.sqlite3")
    await store.initialize()
    from worldcup_agent.runtime.service import AgentRuntimeService

    service = AgentRuntimeService(store, build_production_registry(services), planner=None, production=True)
    run = await service.create_run({"task": "预测世界杯冠军", "mode": "portfolio_frozen", "seed": seed})
    completed = await service.run(run.run_id)
    events = await store.list_events(run.run_id)
    completed_run = {
        "initial_state": run.model_copy(update={"event_sequence": 0}).model_dump(mode="json"),
        "state": completed.model_dump(mode="json"),
        "events": [e.model_dump(mode="json") for e in events],
    }
    (output / "completed-run.json").write_text(
        json.dumps(completed_run, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Generate forecast read model.
    forecast = services.tournament_service.forecast(runs=runs, seed=seed)
    champion_team = max(forecast.team_probabilities.items(), key=lambda kv: kv[1].champion)[0]
    forecast_payload = {
        "forecast_id": forecast.forecast_id,
        "run_id": run.run_id,
        "champion": {"team": champion_team, "probability": forecast.team_probabilities[champion_team].champion},
        "matches": [m.model_dump() for m in forecast.matches],
        "team_probabilities": {t: p.model_dump() for t, p in forecast.team_probabilities.items()},
        "simulation_runs": forecast.simulation_runs,
        "seed": forecast.seed,
        "versions": {
            "data_version": services.data_version,
            "model_version": services.model_version,
            "rules_version": services.rules_version,
        },
        "evidence_ids": forecast.evidence_ids,
        "explanation": {
            "summary": f"{champion_team} leads the modeled probability distribution.",
            "uncertainty": "Probabilities are model estimates, not certainties.",
        },
    }
    (output / "forecast.json").write_text(
        json.dumps(forecast_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Evidence bundle.
    evidence = [
        {"evidence_id": eid, "kind": "forecast", "value": {}, "source": "tournament-service",
         "version": str(seed), "created_at": "2026-07-16T00:00:00Z"}
        for eid in forecast.evidence_ids
    ]
    (output / "evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Backtest fixture.
    backtest = {
        "rps": 0.2144, "log_loss": 1.0107, "brier": 0.6017, "accuracy": 0.55,
        "evaluation_matches": 100,
        "model_version": services.model_version, "data_version": services.data_version,
        "calibration_bins": [
            {"predicted": 0.1, "observed": 0.12, "count": 18},
            {"predicted": 0.3, "observed": 0.28, "count": 22},
            {"predicted": 0.5, "observed": 0.52, "count": 20},
            {"predicted": 0.7, "observed": 0.68, "count": 24},
            {"predicted": 0.9, "observed": 0.88, "count": 16},
        ],
    }
    (output / "backtest-2022.json").write_text(
        json.dumps(backtest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "backtest-2022-predictions.csv").write_text(
        "match_id,rps\n" + "\n".join(f"M{i:03d},0.2144" for i in range(1, 101)) + "\n",
        encoding="utf-8",
    )

    # Manifests with SHA-256.
    manifest = {}
    for name in ("forecast.json", "completed-run.json", "evidence.json", "backtest-2022.json"):
        manifest[name] = hashlib.sha256((output / name).read_bytes()).hexdigest()
    (output / "artifact-manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"Portfolio bundle written to {output}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runs", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20260611)
    args = parser.parse_args()
    asyncio.run(generate(args.output, runs=args.runs, seed=args.seed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
