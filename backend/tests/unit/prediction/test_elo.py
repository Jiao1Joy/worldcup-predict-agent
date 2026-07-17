from worldcup_agent.prediction.elo import EloEngine, MatchForElo


def test_elo_snapshot_is_captured_before_match_update() -> None:
    engine = EloEngine()
    before = engine.process(
        MatchForElo(home_team="A", away_team="B", home_score=3, away_score=0, tournament="FIFA World Cup", neutral=True)
    )

    assert before.home_rating == 1500
    assert before.away_rating == 1500
    assert engine.rating("A") > 1500
    assert engine.rating("B") < 1500


def test_neutral_match_has_no_home_adjustment() -> None:
    engine = EloEngine()
    probability = engine.expected_home_score("A", "B", neutral=True)
    assert probability == 0.5
