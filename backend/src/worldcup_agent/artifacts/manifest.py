from pydantic import BaseModel, Field


class ArtifactFile(BaseModel):
    path: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class ModelArtifactManifest(BaseModel):
    model_version: str
    data_version: str
    trained_until: str
    validation_window: list[str]
    selected_goal_model: str
    goal_parameters: dict[str, float | str | bool] = Field(default_factory=dict)
    fusion_weights: dict[str, float]
    calibrator: str
    files: list[ArtifactFile]
    metrics: dict[str, float]
    degraded: bool = False
