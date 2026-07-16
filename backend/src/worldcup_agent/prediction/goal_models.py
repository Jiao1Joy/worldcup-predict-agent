from math import exp, factorial

import numpy as np
from pydantic import BaseModel
from scipy.optimize import minimize
from scipy.stats import poisson


def _normalize(matrix: np.ndarray) -> np.ndarray:
    matrix = np.clip(matrix, 0.0, None)
    total = float(matrix.sum())
    if total <= 0:
        raise ValueError("score matrix has no probability mass")
    return matrix / total


def poisson_matrix(home_lambda: float, away_lambda: float, max_goals: int = 8) -> np.ndarray:
    goals = np.arange(max_goals + 1)
    return _normalize(np.outer(poisson.pmf(goals, home_lambda), poisson.pmf(goals, away_lambda)))


def bivariate_poisson_matrix(lambda_home: float, lambda_away: float, shared: float, max_goals: int = 8) -> np.ndarray:
    matrix = np.zeros((max_goals + 1, max_goals + 1), dtype=float)
    base = exp(-(lambda_home + lambda_away + shared))
    for home in range(max_goals + 1):
        for away in range(max_goals + 1):
            matrix[home, away] = base * sum(
                lambda_home ** (home - k) * lambda_away ** (away - k) * shared**k
                / (factorial(home - k) * factorial(away - k) * factorial(k))
                for k in range(min(home, away) + 1)
            )
    return _normalize(matrix)


def dixon_coles_matrix(home_lambda: float, away_lambda: float, rho: float, max_goals: int = 8) -> np.ndarray:
    matrix = poisson_matrix(home_lambda, away_lambda, max_goals)
    factors = {
        (0, 0): 1 - home_lambda * away_lambda * rho,
        (1, 0): 1 + away_lambda * rho,
        (0, 1): 1 + home_lambda * rho,
        (1, 1): 1 - rho,
    }
    for score, factor in factors.items():
        matrix[score] *= factor
    return _normalize(matrix)


class GoalModelParameters(BaseModel):
    model_name: str
    mu: float
    xi: float
    shared: float = 0.0
    rho: float = 0.0
    objective: float
    converged: bool


def _vectorized_intensities(home_elos, away_elos, neutral_flags, mu, xi, home_goal_advantage=0.08):
    home_elos = np.asarray(home_elos, dtype=float)
    away_elos = np.asarray(away_elos, dtype=float)
    neutrals = np.asarray(neutral_flags, dtype=float)
    difference = (home_elos - away_elos) / 2.0
    adjustment = (1.0 - neutrals) * home_goal_advantage
    home_lambda = np.exp(mu + xi * difference + adjustment)
    away_lambda = np.exp(mu - xi * difference)
    return np.clip(home_lambda, 0.05, 12.0), np.clip(away_lambda, 0.05, 12.0)


def _independent_log_likelihood(home_lambda, away_lambda, home_scores, away_scores, max_goals=12):
    home_scores = np.clip(np.asarray(home_scores), 0, max_goals)
    away_scores = np.clip(np.asarray(away_scores), 0, max_goals)
    home_ll = poisson.logpmf(home_scores, home_lambda)
    away_ll = poisson.logpmf(away_scores, away_lambda)
    return home_ll + away_ll


def fit_goal_model(
    model_name: str,
    home_elos,
    away_elos,
    neutral_flags,
    home_scores,
    away_scores,
) -> GoalModelParameters:
    bounds: dict[str, list[tuple[float, float]]] = {
        "poisson": [(-2.0, 2.0), (-0.01, 0.01)],
        "bivariate_poisson": [(-2.0, 2.0), (-0.01, 0.01), (0.0, 2.0)],
        "dixon_coles": [(-2.0, 2.0), (-0.01, 0.01), (-0.25, 0.25)],
    }
    initials: dict[str, list[float]] = {
        "poisson": [0.2, 0.001],
        "bivariate_poisson": [0.2, 0.001, 0.1],
        "dixon_coles": [0.2, 0.001, -0.05],
    }
    home_scores_arr = np.clip(np.asarray(home_scores), 0, 12)
    away_scores_arr = np.clip(np.asarray(away_scores), 0, 12)

    def objective(parameters) -> float:
        mu, xi, *extra = parameters
        home_lambda, away_lambda = _vectorized_intensities(
            home_elos, away_elos, neutral_flags, mu, xi
        )
        if model_name == "poisson":
            ll = _independent_log_likelihood(home_lambda, away_lambda, home_scores_arr, away_scores_arr)
        elif model_name == "dixon_coles":
            rho = extra[0]
            ll = _independent_log_likelihood(home_lambda, away_lambda, home_scores_arr, away_scores_arr)
            correction = np.zeros_like(home_lambda)
            mask_00 = (home_scores_arr == 0) & (away_scores_arr == 0)
            correction[mask_00] = np.log(np.clip(1 - home_lambda[mask_00] * away_lambda[mask_00] * rho, 1e-12, None))
            mask_10 = (home_scores_arr == 1) & (away_scores_arr == 0)
            correction[mask_10] = np.log(np.clip(1 + away_lambda[mask_10] * rho, 1e-12, None))
            mask_01 = (home_scores_arr == 0) & (away_scores_arr == 1)
            correction[mask_01] = np.log(np.clip(1 + home_lambda[mask_01] * rho, 1e-12, None))
            mask_11 = (home_scores_arr == 1) & (away_scores_arr == 1)
            correction[mask_11] = np.log(np.clip(1 - rho, 1e-12, None))
            ll = ll + correction
        else:  # bivariate_poisson: shared covariance inflates both by `shared`
            shared = extra[0]
            ll = _independent_log_likelihood(
                home_lambda + shared, away_lambda + shared, home_scores_arr, away_scores_arr
            )
        return float(-np.sum(ll))

    result = minimize(objective, initials[model_name], bounds=bounds[model_name], method="L-BFGS-B")
    if not result.success:
        raise RuntimeError("goal model optimization failed")
    mu, xi, *extra = result.x
    return GoalModelParameters(
        model_name=model_name,
        mu=float(mu),
        xi=float(xi),
        shared=float(extra[0]) if model_name == "bivariate_poisson" else 0.0,
        rho=float(extra[0]) if model_name == "dixon_coles" else 0.0,
        objective=float(result.fun),
        converged=True,
    )


def fit_poisson(*args) -> GoalModelParameters:
    return fit_goal_model("poisson", *args)


def fit_bivariate_poisson(*args) -> GoalModelParameters:
    return fit_goal_model("bivariate_poisson", *args)


def fit_dixon_coles(*args) -> GoalModelParameters:
    return fit_goal_model("dixon_coles", *args)
