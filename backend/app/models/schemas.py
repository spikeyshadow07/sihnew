from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal

class HumanReviewSubmit(BaseModel):
    reviewer_id: str = Field("BITHAWK reviewer", min_length=1, max_length=64)
    decision: Literal["approved", "rejected"]
    notes: str = Field("", max_length=4000)

class WhatIfRequest(BaseModel):
    event_id: str
    modified_participant_id: int
    speed_factor: float = Field(1., ge=.25, le=1.5, allow_inf_nan=False)
    delay_seconds: float = Field(0., ge=0, le=1, allow_inf_nan=False)
    model_config = ConfigDict(extra="forbid")
