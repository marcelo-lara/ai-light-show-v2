from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class FeatureSeries:
    name: str
    source: str
    path: Path
    part: Optional[str]
    duration: Optional[float]
    sample_rate: Optional[float]
    times: List[float] = field(default_factory=list)
    values: List[float] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SongIndex:
    song: str
    song_dir: Path
    info: Dict[str, Any]
    features: Dict[str, FeatureSeries]
    signature: Dict[str, float]
