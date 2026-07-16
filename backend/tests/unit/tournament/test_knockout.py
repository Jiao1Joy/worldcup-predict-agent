from worldcup_agent.tournament.group_stage import StandingRow
from worldcup_agent.tournament.knockout import rank_best_thirds


def test_best_thirds_use_points_goal_difference_goals_fair_play_and_ranking() -> None:
    third_rows = type("R", (), {
        "rows": [
            StandingRow(team="G1", played=3, points=4, goals_for=3, goals_against=2, fair_play=0, fifa_ranking=10),
            StandingRow(team="G2", played=3, points=4, goals_for=3, goals_against=2, fair_play=0, fifa_ranking=20),
            StandingRow(team="G3", played=3, points=4, goals_for=4, goals_against=2, fair_play=0, fifa_ranking=30),
            StandingRow(team="G4", played=3, points=4, goals_for=3, goals_against=3, fair_play=0, fifa_ranking=5),
            StandingRow(team="G5", played=3, points=3, goals_for=5, goals_against=2, fair_play=0, fifa_ranking=40),
            StandingRow(team="G6", played=3, points=3, goals_for=4, goals_against=2, fair_play=0, fifa_ranking=50),
            StandingRow(team="G7", played=3, points=3, goals_for=4, goals_against=2, fair_play=-1, fifa_ranking=60),
            StandingRow(team="G8", played=3, points=3, goals_for=4, goals_against=2, fair_play=0, fifa_ranking=70),
            StandingRow(team="G9", played=3, points=2, goals_for=1, goals_against=1, fair_play=0, fifa_ranking=80),
            StandingRow(team="G10", played=3, points=2, goals_for=1, goals_against=2, fair_play=0, fifa_ranking=90),
            StandingRow(team="G11", played=3, points=1, goals_for=1, goals_against=3, fair_play=0, fifa_ranking=100),
            StandingRow(team="G12", played=3, points=0, goals_for=0, goals_against=4, fair_play=0, fifa_ranking=110),
        ],
    })()
    selected = rank_best_thirds(third_rows.rows)
    assert len(selected) == 8
    # Best four: the 4-point teams, ordered by GD/GF/FIFA.
    assert selected[0].team == "G3"  # best GD + GF among 4-pt
    assert selected[1].team == "G1"  # FIFA ranking tiebreak over G2
    assert selected[2].team == "G2"
    assert selected[3].team == "G4"
    # Next four: 3-point teams.
    assert set(r.team for r in selected[4:]) == {"G5", "G6", "G7", "G8"}
