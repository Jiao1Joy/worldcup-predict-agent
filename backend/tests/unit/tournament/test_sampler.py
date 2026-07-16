import numpy as np
import pytest

from worldcup_agent.tournament.sampler import sample_group_score, sample_knockout_winner


def test_group_score_uses_score_matrix() -> None:
    matrix = np.zeros((3, 3))
    matrix[2, 1] = 1.0
    assert sample_group_score(matrix, np.random.default_rng(7)) == (2, 1)


def test_knockout_draw_reaches_extra_time_and_penalties() -> None:
    matrix = np.zeros((2, 2))
    matrix[0, 0] = 1.0
    result = sample_knockout_winner("A", "B", matrix, np.random.default_rng(7), penalty_home_probability=0.5)
    assert result.winner in {"A", "B"}
    assert result.decided_by in {"extra_time", "penalties"}


def test_sample_frequency_matches_matrix_probabilities() -> None:
    matrix = np.array([[0.2, 0.3], [0.4, 0.1]])
    rng = np.random.default_rng(20260611)
    samples = [sample_group_score(matrix, rng) for _ in range(10000)]
    counts = {(0, 0): 0, (0, 1): 0, (1, 0): 0, (1, 1): 0}
    for s in samples:
        counts[s] += 1
    for (h, a), expected in [((0, 0), 0.2), ((0, 1), 0.3), ((1, 0), 0.4), ((1, 1), 0.1)]:
        assert counts[(h, a)] / 10000 == pytest.approx(expected, abs=0.02)
