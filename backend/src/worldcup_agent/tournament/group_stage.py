from __future__ import annotations

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
    fair_play_home: int = 0
    fair_play_away: int = 0


@dataclass
class StandingRow:
    team: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0
    fair_play: int = 0
    fifa_ranking: int = 0

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    def sort_key(self) -> tuple:
        return (
            self.points,
            self.goal_difference,
            self.goals_for,
            -self.fair_play,
            -self.fifa_ranking,
        )


def create_group_matches(group: str, teams: list[str]) -> list[ScheduledGroupMatch]:
    if len(teams) != 4 or len(set(teams)) != 4:
        raise ValueError("group must contain four unique teams")
    return [
        ScheduledGroupMatch(f"{group}-G{index}", group, home, away)
        for index, (home, away) in enumerate(combinations(teams, 2), start=1)
    ]


def _build_rows(results: list[GroupResult], fifa_rankings: dict[str, int]) -> dict[str, StandingRow]:
    teams = set()
    for result in results:
        teams.add(result.home_team)
        teams.add(result.away_team)
    rows = {team: StandingRow(team=team, fifa_ranking=fifa_rankings.get(team, 9999)) for team in teams}
    for result in results:
        home = rows[result.home_team]
        away = rows[result.away_team]
        home.played += 1
        away.played += 1
        home.goals_for += result.home_goals
        home.goals_against += result.away_goals
        away.goals_for += result.away_goals
        away.goals_against += result.home_goals
        home.fair_play += result.fair_play_home
        away.fair_play += result.fair_play_away
        if result.home_goals > result.away_goals:
            home.wins += 1
            home.points += 3
            away.losses += 1
        elif result.home_goals < result.away_goals:
            away.wins += 1
            away.points += 3
            home.losses += 1
        else:
            home.draws += 1
            away.draws += 1
            home.points += 1
            away.points += 1
    return rows


def _mini_table(results: list[GroupResult], tied_teams: set[str], fifa_rankings: dict[str, int]) -> dict[str, StandingRow]:
    filtered = [
        result
        for result in results
        if result.home_team in tied_teams and result.away_team in tied_teams
    ]
    return _build_rows(filtered, fifa_rankings)


def _rank_tied_subset(
    results: list[GroupResult],
    tied_teams: list[str],
    rows: dict[str, StandingRow],
    fifa_rankings: dict[str, int],
) -> list[str]:
    """Order a subset of teams that share the same points using FIFA tie-breakers."""
    if len(tied_teams) == 1:
        return list(tied_teams)

    tied_set = set(tied_teams)
    mini = _mini_table(results, tied_set, fifa_rankings)

    # Apply mini-table criteria: head-to-head points, then h2h GD, then h2h goals.
    mini_groups: dict[tuple, list[str]] = {}
    for team in tied_teams:
        key = (mini[team].points, mini[team].goal_difference, mini[team].goals_for)
        mini_groups.setdefault(key, []).append(team)
    mini_ordered_keys = sorted(mini_groups, reverse=True)

    result: list[str] = []
    for key in mini_ordered_keys:
        teams_in_key = mini_groups[key]
        if len(teams_in_key) == 1:
            result.extend(teams_in_key)
        else:
            # Still tied after head-to-head mini-table: fall back to overall criteria.
            still = sorted(
                teams_in_key,
                key=lambda t: rows[t].sort_key(),
                reverse=True,
            )
            result.extend(still)
    return result


def rank_group(results: list[GroupResult], fifa_rankings: dict[str, int]) -> list[str]:
    if len(results) != 6:
        raise ValueError("group must have exactly 6 results")
    rows = _build_rows(results, fifa_rankings)
    teams = list(rows)

    ordered: list[str] = []
    pending = teams

    while pending:
        # Group remaining teams by points (the primary criterion).
        by_points: dict[int, list[str]] = {}
        for team in pending:
            by_points.setdefault(rows[team].points, []).append(team)
        top_points = max(by_points)
        top_teams = by_points[top_points]

        if len(top_teams) == 1:
            ordered.append(top_teams[0])
            pending = [t for t in pending if t != top_teams[0]]
            continue

        # Multiple teams share the top points: apply tie-breakers to this subset.
        resolved = _rank_tied_subset(results, top_teams, rows, fifa_rankings)
        # Only promote the teams that are strictly separated by head-to-head;
        # re-loop for any remaining unresolved tie to allow mini-table reapplication.
        ordered.append(resolved[0])
        pending = [t for t in pending if t != resolved[0]]

    return ordered
