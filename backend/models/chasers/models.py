from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ChaserEffect(BaseModel):
    beat: float
    fixture_id: str
    effect: str
    duration: float
    data: Dict[str, Any] = Field(default_factory=dict)


class ChaserDefinition(BaseModel):
    name: str
    description: str
    effects: List[ChaserEffect] = Field(default_factory=list)
