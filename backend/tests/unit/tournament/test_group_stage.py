from worldcup_agent.tournament.group_stage import GroupResult, create_group_matches, rank_group


def test_four_team_group_contains_six_unique_matches() -> None:
    matches = create_group_matches("A", ["A1", "A2", "A3", "A4"])
    assert len(matches) == 6
    assert len({frozenset((match.home_team, match.away_team)) for match in matches}) == 6


def test_head_to_head_points_break_overall_goal_difference_tie() -> None:
    results = [
        GroupResult("A", "A1", "A2", 1, 0, fair_play_home=0, fair_play_away=0),
        GroupResult("A", "A1", "A3", 0, 3, 0, 0),
        GroupResult("A", "A1", "A4", 2, 0, 0, 0),
        GroupResult("A", "A2", "A3", 2, 0, 0, 0),
        GroupResult("A", "A2", "A4", 2, 0, 0, 0),
        GroupResult("A", "A3", "A4", 0, 4, 0, 0),
    ]
    ranked = rank_group(results, fifa_rankings={"A1": 10, "A2": 20, "A3": 30, "A4": 40})
    assert ranked.index("A1") < ranked.index("A2")


def test_three_way_recursive_tie_uses_mini_table() -> None:
    # A1, A2, A3 all finish on 3 points; A4 has 0.
    # Head-to-head among {A1,A2,A3}: A1 beats A2, A2 beats A3, A3 beats A1 -> each 3 pts in mini.
    # Must fall through to overall GD/goals/FIFA ranking without crashing.
    results = [
        GroupResult("A", "A1", "A2", 1, 0, 0, 0),
        GroupResult("A", "A1", "A3", 0, 1, 0, 0),
        GroupResult("A", "A1", "A4", 3, 0, 0, 0),
        GroupResult("A", "A2", "A3", 1, 0, 0, 0),
        GroupResult("A", "A2", "A4", 3, 0, 0, 0),
        GroupResult("A", "A3", "A4", 3, 0, 0, 0),
    ]
    ranked = rank_group(results, fifa_rankings={"A1": 10, "A2": 20, "A3": 30, "A4": 40})
    assert ranked[-1] == "A4"
    assert set(ranked[:3]) == {"A1", "A2", "A3"}
    # When everything else is equal, FIFA ranking (ascending) breaks the tie.
    assert ranked[:3] == ["A1", "A2", "A3"]
