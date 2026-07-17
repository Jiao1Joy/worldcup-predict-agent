import hashlib
import json
from pathlib import Path

import joblib

from worldcup_agent.artifacts.manifest import ArtifactFile, ModelArtifactManifest


class ArtifactRepository:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def save_baseline(
        self,
        model,
        data_version: str,
        selected_goal_model: str,
        fusion_weights: dict[str, float],
        metrics: dict[str, float],
        goal_parameters: dict[str, float | str | bool] | None = None,
        trained_until: str = "2022-11-19T23:59:59Z",
        validation_window: list[str] | None = None,
        calibrator: str = "isotonic-v1",
    ) -> ModelArtifactManifest:
        self.root.mkdir(parents=True, exist_ok=True)
        model_version = f"forecast-ensemble-{data_version[:12]}"
        model_path = self.root / f"{model_version}.joblib"
        joblib.dump(model, model_path)
        sha256 = hashlib.sha256(model_path.read_bytes()).hexdigest()
        manifest = ModelArtifactManifest(
            model_version=model_version,
            data_version=data_version,
            trained_until=trained_until,
            validation_window=validation_window or ["2022-11-20", "2022-12-18"],
            selected_goal_model=selected_goal_model,
            goal_parameters=goal_parameters or {},
            fusion_weights=fusion_weights,
            calibrator=calibrator,
            files=[ArtifactFile(path=str(model_path.name), sha256=sha256)],
            metrics=metrics,
        )
        (self.root / f"{model_version}.manifest.json").write_text(
            json.dumps(manifest.model_dump(mode="json"), indent=2), encoding="utf-8"
        )
        return manifest

    def load(self, model_version: str, expected_data_version: str):
        manifest_path = self.root / f"{model_version}.manifest.json"
        manifest = ModelArtifactManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        if manifest.data_version != expected_data_version:
            raise ValueError("artifact data version mismatch")
        for entry in manifest.files:
            path = self.root / entry.path
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != entry.sha256:
                raise ValueError(f"artifact file hash mismatch: {entry.path}")
        model = joblib.load(self.root / manifest.files[0].path)
        return model, manifest
