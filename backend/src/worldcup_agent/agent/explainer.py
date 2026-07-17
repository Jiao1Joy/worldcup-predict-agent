from __future__ import annotations

from pydantic import BaseModel, Field


class ExplanationClaim(BaseModel):
    text: str
    value: float | None = None
    unit: str = ""
    evidence_id: str


class Explanation(BaseModel):
    summary: str
    claims: list[ExplanationClaim] = Field(default_factory=list)
    uncertainty: str
    data_version: str = ""
    model_version: str = ""
    rules_version: str = ""
