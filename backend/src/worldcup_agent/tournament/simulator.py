from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from worldcup_agent.tournament.annex_c import AnnexC
from worldcup_agent.tournament.contracts import MatchSlot, MatchPredictor
from worldcup_agent.tournament.group_stage import GroupResult, rank_group
from worldcup_agent.tournament.knockout import resolve_round_of_32
from worldcup_agent.tournament.rules import TournamentRules
from worldcup_agent.tournament.sampler import sample_group_score, sample_knockout_winner


@dataclass
class TournamentRunResult:
    matches: list[MatchSlot]
    group_standings: dict[str, list[str]]
    qualified_thirds: list[str]
    champion: str
    content_hash: str
    group_results: dict[str, list[GroupResult]] = field(default_factory=dict)


def _fifa_rankings_from_rules(rules: TournamentRules) -> dict[str, int]:
    return rules.fifa_rankings


def _predict_matrix(
    predictor: MatchPredictor,
    match_id: str,
    home_team: str,
    away_team: str,
) -> tuple[Any, float, float, Any]:
    prediction = predictor.predict(match_id, home_team, away_team)
    matrix = np.array(prediction.score_matrix, dtype=float)
    matrix = matrix / matrix.sum()
    return matrix, prediction.expected_home_goals, prediction.expected_away_goals, prediction


class TournamentSimulator:
    def __init__(self, rules: TournamentRules, predictor: MatchPredictor) -> None:
        self.rules = rules
        self.predictor = predictor
        self._fifa_rankings = _fifa_rankings_from_rules(rules)

    def run_once(self, seed: int) -> TournamentRunResult:
        rng = np.random.default_rng(seed)
        annex_c = AnnexC.load(self.rules.annex_c_path)

        matches: list[MatchSlot] = []
        matches_by_id: dict[str, MatchSlot] = {}
        group_results: dict[str, list[GroupResult]] = {}
        group_standings: dict[str, list[str]] = {}

        # 1. Group stage M001-M072.
        for fixture in self.rules.fixtures:
            if fixture["stage"] != "group":
                continue
            group = fixture["group"]
            home_pos = int(fixture["home_source"][2:])
            away_pos = int(fixture["away_source"][2:])
            teams = self.rules.groups[group]
            home_team = teams[home_pos - 1]
            away_team = teams[away_pos - 1]

            matrix, exp_h, exp_a, prediction = _predict_matrix(
                self.predictor, fixture["match_id"], home_team, away_team
            )
            home_goals, away_goals = sample_group_score(matrix, rng)

            slot = MatchSlot(
                match_id=fixture["match_id"],
                stage="group",
                home_source=fixture["home_source"],
                away_source=fixture["away_source"],
                home_team=home_team,
                away_team=away_team,
                prediction=prediction,
                winner=None,
            )
            matches.append(slot)
            matches_by_id[slot.match_id] = slot
            group_results.setdefault(group, []).append(
                GroupResult(group, home_team, away_team, home_goals, away_goals)
            )

        # 2. Rank every group.
        for group, results in group_results.items():
            group_standings[group] = rank_group(results, self._fifa_rankings)

        # 3. Select the eight best third-placed teams across all groups.
        third_rows: list = []
        from worldcup_agent.tournament.group_stage import _build_rows
        from worldcup_agent.tournament.knockout import rank_best_thirds

        for group, results in group_results.items():
            rows = _build_rows(results, self._fifa_rankings)
            third_team = group_standings[group][2]
            third_row = rows[third_team]
            # Tag the row with its group letter so selection returns groups.
            third_row.team = group
            third_rows.append(third_row)
        qualified_third_groups = {row.team for row in rank_best_thirds(third_rows)}

        # 4. Resolve Round of 32 via Annexe C and sample.
        r32_matches = resolve_round_of_32(
            group_standings, annex_c, self.rules.fixtures, qualified_third_groups
        )
        winners: dict[str, str] = {}
        for match in r32_matches:
            matrix, exp_h, exp_a, prediction = _predict_matrix(
                self.predictor, match.match_id, match.home_team, match.away_team
            )
            ko = sample_knockout_winner(match.home_team, match.away_team, matrix, rng, expected_home_goals=exp_h, expected_away_goals=exp_a)
            match.winner = ko.winner
            match.prediction = prediction
            winners[match.match_id] = ko.winner
            matches.append(match)
            matches_by_id[match.match_id] = match

        # 4. Resolve and sample later rounds M089-M104 from W/L sources.
        progression_fixtures = [f for f in self.rules.fixtures if f["stage"] in (
            "round_of_16", "quarter_final", "semi_final", "third_place", "final"
        )]
        for fixture in progression_fixtures:
            home_team = self._resolve_progression(fixture["home_source"], winners, matches_by_id)
            away_team = self._resolve_progression(fixture["away_source"], winners, matches_by_id)
            matrix, exp_h, exp_a, prediction = _predict_matrix(
                self.predictor, fixture["match_id"], home_team, away_team
            )
            ko = sample_knockout_winner(home_team, away_team, matrix, rng, expected_home_goals=exp_h, expected_away_goals=exp_a)
            winners[fixture["match_id"]] = ko.winner
            slot = MatchSlot(
                match_id=fixture["match_id"],
                stage=fixture["stage"],
                home_source=fixture["home_source"],
                away_source=fixture["away_source"],
                home_team=home_team,
                away_team=away_team,
                prediction=prediction,
                winner=ko.winner,
            )
            matches.append(slot)
            matches_by_id[slot.match_id] = slot

        champion = winners["M104"]

        canonical = self._canonical_json(matches, group_standings, champion)
        content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        return TournamentRunResult(
            matches=matches,
            group_standings=group_standings,
            qualified_thirds=sorted(qualified_third_groups),
            champion=champion,
            content_hash=content_hash,
            group_results=group_results,
        )

    def _resolve_progression(
        self, source: str, winners: dict[str, str], matches_by_id: dict[str, MatchSlot]
    ) -> str:
        code = source[0]
        ref = source[1:]
        match_id = f"M{ref}" if ref.isdigit() else ref
        if code == "W":
            if match_id not in winners:
                raise ValueError(f"unresolved winner source {source}")
            return winners[match_id]
        if code == "L":
            winner = winners.get(match_id)
            if winner is None:
                raise ValueError(f"cannot resolve loser of {match_id}")
            target = matches_by_id.get(match_id)
            if target is None:
                raise ValueError(f"missing match {match_id} for loser lookup")
            teams = {target.home_team, target.away_team}
            loser = teams - {winner}
            if len(loser) != 1:
                raise ValueError(f"ambiguous loser for {match_id}")
            return loser.pop()
        raise ValueError(f"unresolvable progression source: {source}")

    def _canonical_json(self, matches: list[MatchSlot], standings: dict[str, list[str]], champion: str) -> str:
        payload = {
            "matches": [
                {
                    "match_id": m.match_id,
                    "stage": m.stage,
                    "home_team": m.home_team,
                    "away_team": m.away_team,
                    "winner": m.winner,
                }
                for m in matches
            ],
            "standings": standings,
            "champion": champion,
        }
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)
