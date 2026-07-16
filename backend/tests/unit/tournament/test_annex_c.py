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
