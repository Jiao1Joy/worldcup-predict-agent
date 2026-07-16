import numpy as np


def fuse_probabilities(probability_sets: dict[str, np.ndarray], weights: dict[str, float]) -> np.ndarray:
    if set(probability_sets) != set(weights):
        raise ValueError("probability sources and weights must match")
    if any(weight < 0 for weight in weights.values()) or abs(sum(weights.values()) - 1.0) > 1e-9:
        raise ValueError("fusion weights must be non-negative and sum to 1")
    result = sum(probability_sets[name] * weights[name] for name in weights)
    return result / result.sum(axis=1, keepdims=True)
