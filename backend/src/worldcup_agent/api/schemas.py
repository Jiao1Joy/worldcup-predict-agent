from pydantic import BaseModel, Field


class CreateRunRequest(BaseModel):
    task: str = Field(min_length=1)
    seed: int = 7
    data_conflict: bool = False


class FailureRequest(BaseModel):
    failure: str


class ApprovalRequest(BaseModel):
    choice: str
    actor: str
