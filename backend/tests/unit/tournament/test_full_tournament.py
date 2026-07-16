from worldcup_agent.tournament.simulator import TournamentSimulator


def test_one_run_plays_all_104_matches_and_one_champion(rules, deterministic_predictor) -> None:
    simulator = TournamentSimulator(rules, deterministic_predictor)
    result = simulator.run_once(seed=20260611)

    assert len(result.matches) == 104
    assert len([match for match in result.matches if match.stage == "group"]) == 72
    assert len([match for match in result.matches if match.stage == "round_of_32"]) == 16
    assert result.champion in rules.team_ids
    assert all(match.winner for match in result.matches if match.stage != "group")


def test_fixed_seed_produces_identical_run_hash(rules, deterministic_predictor) -> None:
    simulator = TournamentSimulator(rules, deterministic_predictor)
    assert simulator.run_once(7).content_hash == simulator.run_once(7).content_hash
