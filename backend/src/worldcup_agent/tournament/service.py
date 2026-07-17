from __future__ import annotations

from collections import defaultdict

import numpy as np

from worldcup_agent.tournament.contracts import (
    MatchSlot,
    StageProbabilities,
    TournamentForecast,
)
from worldcup_agent.tournament.convergence import BatchResult, ConvergenceRecord
from worldcup_agent.tournament.simulator import TournamentSimulator


class TournamentForecastService:
    def __init__(self, simulator: TournamentSimulator, batch_size: int = 500) -> None:
        self.simulator = simulator
        self.batch_size = batch_size

    def forecast(self, runs: int, seed: int, as_of: str | None = None) -> TournamentForecast:
        if runs < 1:
            raise ValueError("runs must be positive")
        convergence = ConvergenceRecord()
        champion_counts: dict[str, int] = defaultdict(int)
        stage_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        representative_runs: dict[str, list[MatchSlot]] = {}
        prev_champion_probs: dict[str, float] = {}

        remaining = runs
        batch_index = 0
        team_ids = self.simulator.rules.team_ids

        while remaining > 0:
            batch_runs = min(self.batch_size, remaining)
            seed_seq = np.random.SeedSequence([seed, batch_index])
            batch_champions: dict[str, int] = defaultdict(int)
            batch_stage: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

            for sub in range(batch_runs):
                sub_seed = int(seed_seq.spawn(1)[0].generate_state(1)[0])
                result = self.simulator.run_once(sub_seed)
                batch_champions[result.champion] += 1
                representative_runs.setdefault(result.champion, result.matches)
                # Track stage progression: a team's deepest stage this run.
                deepest = _deepest_stages(result.matches)
                for team, stage in deepest.items():
                    batch_stage[team][stage] += 1

            batch = BatchResult(
                batch_index=batch_index,
                seed_entropy=[seed, batch_index],
                runs=batch_runs,
                champion_counts=dict(batch_champions),
                content_hash="",
            )
            convergence.batches.append(batch)

            for team, count in batch_champions.items():
                champion_counts[team] += count
            for team, stages in batch_stage.items():
                for stage, count in stages.items():
                    stage_counts[team][stage] += count

            total = sum(champion_counts.values()) or 1
            current_champion_probs = {t: champion_counts.get(t, 0) / total for t in team_ids}
            if prev_champion_probs:
                delta = max(
                    abs(current_champion_probs[t] - prev_champion_probs.get(t, 0.0))
                    for t in team_ids
                )
                convergence.deltas.append(delta)
            prev_champion_probs = current_champion_probs

            remaining -= batch_runs
            batch_index += 1

        total_runs = sum(b.runs for b in convergence.batches)
        team_probabilities: dict[str, StageProbabilities] = {}
        for team in team_ids:
            stage_hits = stage_counts[team]
            r32 = _cumulative_stage_prob(stage_hits, team, total_runs, "round_of_32")
            r16 = _cumulative_stage_prob(stage_hits, team, total_runs, "round_of_16")
            qf = _cumulative_stage_prob(stage_hits, team, total_runs, "quarter_final")
            sf = _cumulative_stage_prob(stage_hits, team, total_runs, "semi_final")
            final = _cumulative_stage_prob(stage_hits, team, total_runs, "final")
            champion = champion_counts.get(team, 0) / total_runs
            # Enforce monotonicity by taking running maxima.
            probs = _monotonic([r32, r16, qf, sf, final, champion])
            team_probabilities[team] = StageProbabilities(
                r32=probs[0], r16=probs[1], qf=probs[2], sf=probs[3], final=probs[4], champion=probs[5]
            )

        forecast_id = f"fc-{seed}-{runs}"
        modal_champion = max(team_ids, key=lambda team: champion_counts.get(team, 0))
        representative_matches = representative_runs[modal_champion]
        versions = {
            "rules_version": self.simulator.rules.rules_version,
            "seed": str(seed),
        }
        return TournamentForecast(
            forecast_id=forecast_id,
            matches=representative_matches,
            team_probabilities=team_probabilities,
            simulation_runs=total_runs,
            seed=seed,
            versions=versions,
            evidence_ids=[f"FORECAST-{forecast_id}", f"SIM-{forecast_id}"],
        )


def _deepest_stages(matches: list[MatchSlot]) -> dict[str, str]:
    """For each team, the furthest stage it reached in this run."""
    stage_rank = {
        "round_of_32": 1,
        "round_of_16": 2,
        "quarter_final": 3,
        "semi_final": 4,
        "third_place": 4,
        "final": 5,
    }
    deepest: dict[str, str] = {}
    for match in matches:
        for team in (match.home_team, match.away_team):
            if team is None:
                continue
            current = deepest.get(team)
            new_stage = match.stage
            if current is None or stage_rank.get(new_stage, 0) > stage_rank.get(current, 0):
                deepest[team] = new_stage
    return deepest


def _cumulative_stage_prob(
    stage_hits: dict[str, int], team: str, total: int, target: str
) -> float:
    stage_rank = {
        "round_of_32": 1,
        "round_of_16": 2,
        "quarter_final": 3,
        "semi_final": 4,
        "third_place": 4,
        "final": 5,
    }
    target_rank = stage_rank[target]
    reached = sum(count for stage, count in stage_hits.items() if stage_rank.get(stage, 0) >= target_rank)
    return reached / total if total else 0.0


def _monotonic(values: list[float]) -> list[float]:
    result = list(values)
    for i in range(1, len(result)):
        result[i] = min(result[i], result[i - 1])
    return result
