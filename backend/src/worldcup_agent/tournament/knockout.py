from __future__ import annotations

from worldcup_agent.tournament.annex_c import AnnexC
from worldcup_agent.tournament.contracts import MatchSlot
from worldcup_agent.tournament.group_stage import StandingRow


def rank_best_thirds(third_rows: list[StandingRow]) -> list[StandingRow]:
    if len(third_rows) != 12:
        raise ValueError("best-third ranking requires exactly 12 third-place rows")
    ordered = sorted(
        third_rows,
        key=lambda r: (r.points, r.goal_difference, r.goals_for, -r.fair_play, -r.fifa_ranking),
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

    # Annexe C maps its 8 bracket slots to the group letters of the thirds that
    # play there. Winner-side "3" placeholders consume these in schedule order;
    # the remaining thirds feed runner-up-side "3" placeholders.
    slot_to_third_group = dict(annex_c.resolve(qualified_third_groups))
    winner_slot_pool = dict(slot_to_third_group)
    runner_third_pool = sorted(qualified_third_groups)

    matches: list[MatchSlot] = []
    for fixture in r32_fixtures:
        home_src = fixture["home_source"]
        away_src = fixture["away_source"]
        home_team = _resolve_side(home_src, group_rankings, winner_slot_pool, runner_third_pool)
        away_team = _resolve_side(away_src, group_rankings, winner_slot_pool, runner_third_pool)
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
    return matches


def _resolve_side(
    source: str,
    group_rankings: dict[str, list[str]],
    winner_slot_pool: dict[str, str],
    runner_third_pool: list[str],
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
        # Prefer an Annexe C winner-slot mapping whose group has not been consumed.
        if winner_slot_pool:
            slot, third_group = next(iter(winner_slot_pool.items()))
            winner_slot_pool.pop(slot)
            if third_group in runner_third_pool:
                runner_third_pool.remove(third_group)
            return group_rankings[third_group][2]
        # Otherwise draw from the remaining qualified thirds (runner-up side).
        if not runner_third_pool:
            raise ValueError("no remaining best-thirds to assign")
        third_group = runner_third_pool.pop(0)
        return group_rankings[third_group][2]
    raise ValueError(f"unresolvable fixture source: {source}")
