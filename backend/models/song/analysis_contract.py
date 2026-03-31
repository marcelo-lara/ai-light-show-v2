from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .beats import Beat


class DominantPart(BaseModel):
    part: str
    mean: float = 0.0
    peak: float = 0.0
    share: float = 0.0


class StemAccent(BaseModel):
    time: float
    end_s: float
    bar: int
    beat: int
    mean: float = 0.0
    min: float = 0.0
    peak_time: float = 0.0
    peak_value: float = 0.0


class StemDip(BaseModel):
    start_s: float
    end_s: float
    mean: float = 0.0
    min: float = 0.0
    neighbor_mean: float = 0.0
    mean_ratio: float = 0.0


class LowWindow(BaseModel):
    start_s: float
    end_s: float
    parts: list[str] = Field(default_factory=list)
    mean_ratio: float = 0.0


class SectionEvent(BaseModel):
    kind: str
    strength: float = 0.0
    dominant_part: str = "mix"
    parts: list[str] = Field(default_factory=list)
    time_s: float | None = None
    start_s: float | None = None
    end_s: float | None = None


class SectionAnalysis(BaseModel):
    name: str
    start_s: float
    end_s: float
    start_bar: int | None = None
    start_beat: int | None = None
    end_bar: int | None = None
    end_beat: int | None = None
    energy: dict[str, Any] = Field(default_factory=dict)
    rhythm: dict[str, Any] = Field(default_factory=dict)
    harmony: dict[str, Any] = Field(default_factory=dict)
    dominant_parts: list[DominantPart] = Field(default_factory=list)
    events: list[SectionEvent] = Field(default_factory=list)
    stem_accents: dict[str, list[StemAccent]] = Field(default_factory=dict)
    stem_dips: dict[str, list[StemDip]] = Field(default_factory=dict)
    low_windows: list[LowWindow] = Field(default_factory=list)


class SongAnalysis(BaseModel):
    song_id: str
    bpm: float
    duration_s: float
    beats_available: bool
    sections_available: bool
    features_available: bool
    hints_available: bool
    available_parts: list[str] = Field(default_factory=list)
    global_energy: dict[str, Any] = Field(default_factory=dict)
    beats: list[Beat] = Field(default_factory=list)
    sections: list[SectionAnalysis] = Field(default_factory=list)