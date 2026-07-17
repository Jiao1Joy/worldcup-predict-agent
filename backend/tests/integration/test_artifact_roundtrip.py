import numpy as np
import pandas as pd
from datetime import UTC, datetime

from worldcup_agent.artifacts.repository import ArtifactRepository
from worldcup_agent.data.contracts import DataSnapshotManifest
from worldcup_agent.prediction.calibration import train_baseline_calibrator
from worldcup_agent.prediction.goal_models import GoalModelParameters
from worldcup_agent.tools.production import ProductionServices


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


def test_production_services_load_trained_snapshot_artifacts(tmp_path, rules_dir) -> None:
    snapshot = pd.DataFrame(
        [
            {
                "date": datetime(2022, 1, 1, tzinfo=UTC),
                "home_team": "Argentina",
                "away_team": "Brazil",
                "home_score": 1,
                "away_score": 0,
                "tournament": "Friendly",
                "neutral": True,
            }
        ]
    )
    snapshot.to_parquet(tmp_path / "snapshot.parquet", index=False)
    snapshot_manifest = DataSnapshotManifest(
        data_version="data-v1",
        source_name="fixture",
        source_uri="fixture://results",
        source_sha256="0" * 64,
        snapshot_cutoff=datetime(2022, 1, 1, tzinfo=UTC),
        row_count=1,
    )
    (tmp_path / "snapshot.manifest.json").write_text(
        snapshot_manifest.model_dump_json(), encoding="utf-8"
    )

    features = np.array(
        [
            [0.6, 0.25, 0.15, 0.55, 0.25, 0.2],
            [0.3, 0.4, 0.3, 0.25, 0.45, 0.3],
            [0.15, 0.25, 0.6, 0.2, 0.25, 0.55],
        ]
    )
    model = train_baseline_calibrator(features, np.array([0, 1, 2]))
    goal_parameters = GoalModelParameters(
        model_name="dixon_coles",
        mu=0.22,
        xi=0.0016,
        rho=-0.08,
        objective=0.0,
        converged=True,
    )
    ArtifactRepository(tmp_path / "artifacts").save_baseline(
        model=model,
        data_version="data-v1",
        selected_goal_model="dixon_coles",
        goal_parameters=goal_parameters.model_dump(),
        fusion_weights={"elo": 0.2, "goal": 0.5, "ml": 0.3},
        metrics={"rps": 0.18, "log_loss": 0.92, "brier": 0.21},
    )

    services = ProductionServices.from_artifacts(str(tmp_path), str(rules_dir))
    prediction = services.prediction_service.predict(
        "M001", "Argentina", "Brazil", 1550.0, 1500.0, True
    )
    assert services.data_version == "data-v1"
    assert prediction.model_version == services.model_version
