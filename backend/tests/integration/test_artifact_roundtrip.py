import numpy as np

from worldcup_agent.artifacts.repository import ArtifactRepository
from worldcup_agent.prediction.calibration import train_baseline_calibrator


def test_trained_calibrator_round_trips_with_manifest(tmp_path) -> None:
    features = np.array([[0.6, 0.2, 0.2], [0.2, 0.5, 0.3], [0.1, 0.2, 0.7]])
    labels = np.array([0, 1, 2])
    model = train_baseline_calibrator(features, labels)
    repository = ArtifactRepository(tmp_path)

    manifest = repository.save_baseline(
        model=model,
        data_version="data-v1",
        selected_goal_model="dixon_coles",
        fusion_weights={"elo": 0.2, "goal": 0.5, "ml": 0.3},
        metrics={"rps": 0.18, "log_loss": 0.92, "brier": 0.21},
    )
    loaded, loaded_manifest = repository.load(manifest.model_version, expected_data_version="data-v1")

    assert loaded.predict_proba(features).shape == (3, 3)
    assert loaded_manifest.files[0].sha256


def test_repository_rejects_mismatched_data_version(tmp_path) -> None:
    features = np.array([[0.6, 0.2, 0.2], [0.2, 0.5, 0.3], [0.1, 0.2, 0.7]])
    labels = np.array([0, 1, 2])
    model = train_baseline_calibrator(features, labels)
    repository = ArtifactRepository(tmp_path)
    manifest = repository.save_baseline(
        model=model,
        data_version="data-v1",
        selected_goal_model="dixon_coles",
        fusion_weights={"elo": 0.2, "goal": 0.5, "ml": 0.3},
        metrics={"rps": 0.18, "log_loss": 0.92, "brier": 0.21},
    )
    import pytest

    with pytest.raises(ValueError, match="data version mismatch"):
        repository.load(manifest.model_version, expected_data_version="data-v2")
