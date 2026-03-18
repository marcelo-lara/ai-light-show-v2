from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class CueEntry(BaseModel):
    time: float
    fixture_id: Optional[str] = None
    effect: Optional[str] = None
    duration: Optional[float] = None
    chaser_id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    name: Optional[str] = None
    created_by: str = "user"

    @model_validator(mode="after")
    def validate_shape(self) -> "CueEntry":
        has_chaser = bool(self.chaser_id)
        has_effect_fields = bool(self.fixture_id or self.effect or self.duration is not None)
        if has_chaser == has_effect_fields:
            raise ValueError("cue_entry_must_define_effect_or_chaser")
        if has_chaser:
            return self
        if not self.fixture_id:
            raise ValueError("cue_entry_missing_fixture_id")
        if not self.effect:
            raise ValueError("cue_entry_missing_effect")
        if self.duration is None:
            self.duration = 0.0
        return self

    @property
    def is_chaser(self) -> bool:
        return bool(self.chaser_id)


class CueSheet(BaseModel):
    song_filename: str
    entries: List[CueEntry] = Field(default_factory=list)
