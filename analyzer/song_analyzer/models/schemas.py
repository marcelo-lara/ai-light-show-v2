from __future__ import annotations
from pydantic import BaseModel
from typing import List, Optional, Any


class FailureRecord(BaseModel):
    code: str
    message: str
    detail: Optional[str]
    exception_type: Optional[str]
    retryable: bool = False


class StepRecord(BaseModel):
    name: str
    status: str
    artifacts: List[str]
    seconds: float
    failure: Optional[FailureRecord]


class RunSchema(BaseModel):
    schema_version: str = "1.0"
    generated_at: Optional[str]
    song: Optional[dict]
    environment: Optional[dict]
    steps: List[StepRecord] = []
