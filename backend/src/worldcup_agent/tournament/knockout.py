from __future__ import annotations

from worldcup_agent.tournament.annex_c import AnnexC
from worldcup_agent.tournament.contracts import MatchSlot
from worldcup_agent.tournament.group_stage import StandingRow


def rank_best_thirds(third_rows: list[StandingRow]) -> list[StandingRow]:
    if len(third_rows) != 12:
        raise ValueError("best-third ranking requires exactly 12 third-place rows")
    ordered = sorted(
        third_rows,
        key=lambda r: (r.points, r.goal_difference, r.goals_for, r.fair_play, -r.fifa_ranking),
        reverse=True,
    )
    return ordered[:8]


def resolve_round_of_32(
    group_rankings: dict[str, list[str]],
    annex_c: AnnexC,
    fixture_slots: list[dict],
    qualified_third_groups: set[str] | None = None,
) -> list[MatchSlot]:
    r32_fixtures = [f for f in fixture_slots if f["stage"] == "round_of_32"]
    if len(r32_fixtures) != 16:
        raise ValueError("round of 32 must contain 16 matches")
    if qualified_third_groups is None or len(qualified_third_groups) != 8:
        raise ValueError("exactly eight best-third groups must qualify")

    # Annexe C maps each of the eight group-winner slots (1A, 1B, 1D, 1E,
    # 1G, 1I, 1K and 1L) to the qualified third-place group it must face.
    slot_to_third_group = dict(annex_c.resolve(qualified_third_groups))
    used_third_slots: set[str] = set()

    matches: list[MatchSlot] = []
    for fixture in r32_fixtures:
        home_src = fixture["home_source"]
        away_src = fixture["away_source"]
        home_team = _resolve_side(
            home_src, away_src, group_rankings, slot_to_third_group, used_third_slots
        )
        away_team = _resolve_side(
            away_src, home_src, group_rankings, slot_to_third_group, used_third_slots
        )
        matches.append(
            MatchSlot(
                match_id=fixture["match_id"],
                stage="round_of_32",
                home_source=home_src,
                away_source=away_src,
                home_team=home_team,
                away_team=away_team,
            )
        )

    teams = [t for m in matches for t in (m.home_team, m.away_team)]
    if len(teams) != len(set(teams)):
        raise ValueError("round of 32 contains duplicate teams")
    if len(teams) != 32:
        raise ValueError("round of 32 must contain 32 unique teams")
    if used_third_slots != set(slot_to_third_group):
        raise ValueError("round of 32 does not consume every Annexe C winner slot exactly once")
    return matches


def _resolve_side(
    source: str,
    opponent_source: str,
    group_rankings: dict[str, list[str]],
    slot_to_third_group: dict[str, str],
    used_third_slots: set[str],
) -> str:
    if source.startswith(("W", "L")):
        return source
    position = source[0]
    if position in ("1", "2"):
        group = source[1]
        ranked = group_rankings.get(group)
        if ranked is None:
            raise ValueError(f"unknown group {group} in source {source}")
        return ranked[int(position) - 1]
    if position == "3":
        if opponent_source not in slot_to_third_group:
            raise ValueError(
                f"third-place source must face an Annexe C winner slot, got {opponent_source}"
            )
        if opponent_source in used_third_slots:
            raise ValueError(f"Annexe C winner slot used twice: {opponent_source}")
        used_third_slots.add(opponent_source)
        third_group = slot_to_third_group[opponent_source]
        return group_rankings[third_group][2]
    raise ValueError(f"unresolvable fixture source: {source}")
