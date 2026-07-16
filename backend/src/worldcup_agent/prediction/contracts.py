from pydantic import BaseModel, Field, model_validator


class OutcomeProbabilities(BaseModel):
    home: float = Field(ge=0, le=1)
    draw: float = Field(ge=0, le=1)
    away: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def normalized(self):
        if abs(self.home + self.draw + self.away - 1.0) > 1e-9:
            raise ValueError("outcome probabilities must sum to 1")
        return self


class MatchPrediction(BaseModel):
    match_id: str
    home_team: str
    away_team: str
    expected_home_goals: float = Field(ge=0)
    expected_away_goals: float = Field(ge=0)
    outcomes: OutcomeProbabilities
    score_matrix: list[list[float]]
    data_version: str
    model_version: str
    evidence_ids: list[str] = Field(default_factory=list)

    @classmethod
    def from_score_matrix(cls, **values):
        matrix = values.pop("score_matrix")
        total = sum(sum(row) for row in matrix)
        if total <= 0:
            raise ValueError("score matrix must contain positive probability")
        normalized = [[cell / total for cell in row] for row in matrix]
        home = sum(cell for i, row in enumerate(normalized) for j, cell in enumerate(row) if i > j)
        draw = sum(row[i] for i, row in enumerate(normalized) if i < len(row))
        away = 1.0 - home - draw
        return cls(
            **values,
            score_matrix=normalized,
            outcomes=OutcomeProbabilities(home=home, draw=draw, away=away),
        )
