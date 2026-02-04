"""Configuration management for the song analyzer."""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class AnalysisConfig(BaseModel):
    """Configuration for the analysis pipeline."""

    # Paths
    songs_dir: Path = Field(default=Path("songs"))
    temp_dir: Path = Field(default=Path("temp_files"))
    metadata_dir: Path = Field(default=Path("metadata"))

    # Device settings
    device: str = Field(default="auto")  # auto, cuda, cpu

    # Model settings
    stems_model: str = Field(default="htdemucs_ft")

    # Processing settings
    overwrite: bool = Field(default=False)

    # Output settings
    json_precision: int = Field(default=6)

    @classmethod
    def from_env(cls) -> "AnalysisConfig":
        """Create config from environment variables."""
        return cls(
            songs_dir=Path(os.getenv("SONGS_DIR", "songs")),
            temp_dir=Path(os.getenv("TEMP_DIR", "temp_files")),
            metadata_dir=Path(os.getenv("METADATA_DIR", "metadata")),
            device=os.getenv("DEVICE", "auto"),
            stems_model=os.getenv("STEMS_MODEL", "htdemucs_ft"),
            overwrite=os.getenv("OVERWRITE", "false").lower() == "true",
        )


class AnalysisContext(BaseModel):
    """Context passed to each analysis step."""

    config: AnalysisConfig
    song_path: Path
    song_slug: str
    output_dir: Path
    temp_dir: Path
    run_timestamp: datetime = Field(default_factory=datetime.utcnow)

    @property
    def analysis_dir(self) -> Path:
        """Directory for analysis artifacts."""
        return self.output_dir / "analysis"

    @property
    def show_plan_dir(self) -> Path:
        """Directory for show plan artifacts."""
        return self.output_dir / "show_plan"

    def ensure_dirs(self):
        """Ensure all required directories exist."""
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        self.show_plan_dir.mkdir(parents=True, exist_ok=True)