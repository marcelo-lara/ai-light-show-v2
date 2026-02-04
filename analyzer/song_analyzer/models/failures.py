from pydantic import BaseModel
from typing import Optional


class FailureRecord(BaseModel):
    code: str
    message: str
    detail: Optional[str] = None
    exception_type: Optional[str] = None
    retryable: bool = False
