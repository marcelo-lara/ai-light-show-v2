from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    meta_root: Path
    host: str
    port: int
    transport: str
    max_raw_points: int
    default_max_points: int



def load_settings() -> Settings:
    return Settings(
        meta_root=Path(os.getenv("SONG_METADATA_MCP_META_ROOT", "/app/meta")),
        host=os.getenv("SONG_METADATA_MCP_HOST", "0.0.0.0"),
        port=int(os.getenv("SONG_METADATA_MCP_PORT", "8081")),
        transport=os.getenv("SONG_METADATA_MCP_TRANSPORT", "sse"),
        max_raw_points=int(os.getenv("SONG_METADATA_MCP_MAX_RAW_POINTS", "20000")),
        default_max_points=int(os.getenv("SONG_METADATA_MCP_DEFAULT_MAX_POINTS", "5000")),
    )
