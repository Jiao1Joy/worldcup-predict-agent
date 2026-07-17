from itertools import combinations

from worldcup_agent.tournament.annex_c import AnnexC


def test_annex_c_covers_every_eight_group_combination(rules_dir) -> None:
    table = AnnexC.load(rules_dir / "annex_c.csv")
    expected = {"".join(groups) for groups in combinations("ABCDEFGHIJKL", 8)}
    assert set(table.combinations) == expected
    assert len(table.combinations) == 495


def test_each_mapping_uses_each_qualified_group_once(rules_dir) -> None:
    table = AnnexC.load(rules_dir / "annex_c.csv")
    for combination, slots in table.combinations.items():
        assert sorted(slots.values()) == sorted(combination)
        assert len(slots) == 8


def test_rules_load_validates_hashes_and_structure(rules_dir) -> None:
    from worldcup_agent.tournament.rules import load_rules

    rules = load_rules(rules_dir)
    assert len(rules.team_ids) == 48
    assert len(rules.fixtures) == 104
    assert rules.fixtures_by_id["M001"]["stage"] == "group"
    assert rules.fixtures_by_id["M104"]["stage"] == "final"
    assert rules.fifa_rankings["Argentina"] == 1
    assert rules.fifa_rankings["New Zealand"] == 85


def test_official_knockout_sources_are_versioned(rules_dir) -> None:
    from worldcup_agent.tournament.rules import load_rules

    rules = load_rules(rules_dir)
    expected = {
        "M073": ("2A", "2B"),
        "M074": ("1E", "3"),
        "M079": ("1A", "3"),
        "M089": ("W074", "W077"),
        "M098": ("W093", "W094"),
        "M104": ("W101", "W102"),
    }
    assert {
        match_id: (
            rules.fixtures_by_id[match_id]["home_source"],
            rules.fixtures_by_id[match_id]["away_source"],
        )
        for match_id in expected
    } == expected


def test_annex_c_maps_thirds_to_the_named_winner_slots(rules_dir) -> None:
    from worldcup_agent.tournament.knockout import resolve_round_of_32
    from worldcup_agent.tournament.rules import load_rules

    rules = load_rules(rules_dir)
    standings = {group: [f"{group}{position}" for position in range(1, 5)] for group in "ABCDEFGHIJKL"}
    matches = resolve_round_of_32(
        standings,
        AnnexC.load(rules_dir / "annex_c.csv"),
        rules.fixtures,
        set("EFGHIJKL"),
    )
    by_id = {match.match_id: match for match in matches}
    assert by_id["M079"].away_team == "E3"  # slot 1A -> group E third
    assert by_id["M074"].away_team == "F3"  # slot 1E -> group F third
    assert by_id["M087"].away_team == "L3"  # slot 1K -> group L third
