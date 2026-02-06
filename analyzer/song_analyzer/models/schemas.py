"""Data models and schemas for analysis artifacts."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class FailureRecord(BaseModel):
    """Record of a step failure."""

    code: str = Field(..., description="Failure code")
    message: str = Field(..., description="Human readable summary")
    detail: Optional[str] = Field(None, description="Optional long detail")
    exception_type: Optional[str] = Field(None, description="Exception type")
    retryable: bool = Field(False, description="Whether the failure is retryable")


class StepResult(BaseModel):
    """Result of running an analysis step."""

    artifacts_written: List[Path] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    failure: Optional[FailureRecord] = Field(None)


class StepRun(BaseModel):
    """Record of a step execution."""

    name: str
    status: str  # "ok", "failed", "skipped"
    artifacts: List[str] = Field(default_factory=list)
    seconds: float
    failure: Optional[FailureRecord] = Field(None)


class RunRecord(BaseModel):
    """Record of a complete analysis run."""

    schema_version: str = "1.0"
    generated_at: str
    song: Dict[str, Any]
    environment: Dict[str, Any]
    steps: List[StepRun]


class TimelineArtifact(BaseModel):
    """Timeline metadata artifact."""

    schema_version: str = "1.0"
    song_slug: str
    duration_s: float
    sample_rate_hz: int
    channels: int
    source_audio: Dict[str, str]


class StemsArtifact(BaseModel):
    """Stem separation artifact."""

    schema_version: str = "1.0"
    status: str
    model: Dict[str, Any]
    stems: Dict[str, str]


class BeatsArtifact(BaseModel):
    """Beat tracking artifact."""

    schema_version: str = "1.0"
    source: Dict[str, Any]
    beats: List[float]
    downbeats: List[float]
    tempo: Dict[str, Any]


class EnergyArtifact(BaseModel):
    """Energy curves artifact."""

    schema_version: str = "1.0"
    fps: int
    unit: str
    tracks: Dict[str, Dict[str, List[float]]]


class OnsetsArtifact(BaseModel):
    """Drum onsets artifact."""

    schema_version: str = "1.0"
    source: Dict[str, Any]
    events: List[Dict[str, Any]]


class VocalsArtifact(BaseModel):
    """Vocal activity artifact."""

    schema_version: str = "1.0"
    source: Dict[str, Any]
    segments: List[Dict[str, Any]]
    phrases: List[Dict[str, Any]]


class SectionsArtifact(BaseModel):
    """Song sections artifact."""

    schema_version: str = "1.0"
    source: Dict[str, Any]
    sections: List[Dict[str, Any]]


class PatternsArtifact(BaseModel):
    """Drum patterns artifact."""

    schema_version: str = "1.0"
    grid: Dict[str, Any]
    patterns: List[Dict[str, Any]]
    occurrences: List[Dict[str, Any]]


class RolesArtifact(BaseModel):
    """Musical roles artifact."""

    schema_version: str = "1.0"
    roles: Dict[str, Dict[str, Any]]


class MomentsArtifact(BaseModel):
    """Notable moments artifact."""

    schema_version: str = "1.0"
    moments: List[Dict[str, Any]]


class ShowPlanArtifact(BaseModel):
    """Show plan index artifact."""

    includes: Dict[str, str]
    meta: Dict[str, Any]