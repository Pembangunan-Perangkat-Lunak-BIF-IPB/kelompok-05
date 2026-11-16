from typing import Optional
from pydantic import BaseModel, Field, model_validator
from models import VisibilityType

class VisibilityUpdateRequest(BaseModel):
    visibility: VisibilityType

class ExecutionParameters(BaseModel):
    min_dp: int = Field(default=10, ge=1)

    min_mq: int = Field(
        default=30,
        ge=0,
        le=60
    )

    min_base_quality: int = Field(
        default=20,
        ge=0,
        le=60
    )

    max_depth: int = Field(
        default=10000,
        ge=100,
        le=100000
    )

    min_qual: float = Field(default=30.0, ge=0)

    min_af: float = Field(
        default=0.20,
        ge=0.01,
        le=1
    )

class RunConfiguration(BaseModel):
    execution_mode: str = Field(default="default", pattern="^(default|custom)$")
    parameters: Optional[ExecutionParameters] = None

    @model_validator(mode="after")
    def check_mode(self):
        if self.execution_mode == "custom" and self.parameters is None:
            raise ValueError("Mode custom membutuhkan objek parameters")
        return self
