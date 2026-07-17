from worldcup_agent.runtime.policies import next_simulation_action, snapshot_action


def test_stale_snapshot_requires_refresh() -> None:
    assert snapshot_action(age_hours=25) == "refresh_snapshot"
    assert snapshot_action(age_hours=2) == "continue"


def test_unconverged_simulation_adds_runs() -> None:
    assert next_simulation_action(probability_delta=0.018, total_runs=20_000) == "simulate_more"
    assert next_simulation_action(probability_delta=0.004, total_runs=30_000) == "critique"
