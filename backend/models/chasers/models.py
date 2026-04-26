from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChaserEffect(BaseModel):
    beat: float
    fixture_id: str
    effect: str
    duration: float
    data: Dict[str, Any] = Field(default_factory=dict)


class ChaserDefinition(BaseModel):
    id: str
    name: str
    description: str
    effects: List[ChaserEffect] = Field(default_factory=list)

    # Dynamic generation support
    type: str = "static"  # "static" or "dynamic"
    generator_id: Optional[str] = None
    default_params: Dict[str, Any] = Field(default_factory=dict)
