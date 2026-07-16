import numpy as np
import pytest

from worldcup_agent.prediction.goal_models import bivariate_poisson_matrix, dixon_coles_matrix, poisson_matrix


@pytest.mark.parametrize(
    ("factory", "args"),
    [
        (poisson_matrix, (1.4, 0.9)),
        (bivariate_poisson_matrix, (1.2, 0.7, 0.2)),
        (dixon_coles_matrix, (1.4, 0.9, -0.08)),
    ],
)
def test_score_matrix_is_non_negative_and_normalized(factory, args) -> None:
    matrix = factory(*args, max_goals=8)
    assert matrix.shape == (9, 9)
    assert np.all(matrix >= 0)
    assert matrix.sum() == pytest.approx(1.0)


def test_dixon_coles_changes_low_score_mass() -> None:
    baseline = poisson_matrix(1.4, 0.9, max_goals=8)
    corrected = dixon_coles_matrix(1.4, 0.9, rho=-0.08, max_goals=8)
    assert corrected[0, 0] != pytest.approx(baseline[0, 0])
