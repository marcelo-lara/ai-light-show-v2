# pyright: reportAttributeAccessIssue=false

import contextlib
from pathlib import Path
from typing import Any, List, Optional

from models.song import SongMetadata

from ..constants import MAX_SONG_SECONDS


class StateCoreMetadataMixin:
    def _infer_song_length_seconds(self, metadata: SongMetadata) -> float:
        raw = getattr(metadata, "duration", None)
        if isinstance(raw, (int, float)) and raw > 0:
            return float(raw)

        max_t = 0.0
        with contextlib.suppress(TypeError, ValueError):
            for _name, rng in (metadata.parts or {}).items():
                if isinstance(rng, list) and len(rng) >= 2:
                    max_t = max(max_t, float(rng[1]))
        with contextlib.suppress(TypeError, ValueError):
            for _name, times in (metadata.hints or {}).items():
                for t in times or []:
                    max_t = max(max_t, float(t))
        with contextlib.suppress(TypeError, ValueError):
            for _name, times in (metadata.drums or {}).items():
                for t in times or []:
                    max_t = max(max_t, float(t))
        if max_t <= 0:
            max_t = float(MAX_SONG_SECONDS)
        return min(float(MAX_SONG_SECONDS), max_t)

    def _meta_candidates(self, song_filename: str) -> List[Path]:
        return self.song_metadata_loader.meta_candidates(song_filename)

    def _resolve_analyzer_artifact_path(self, raw_path: Any, meta_file: Path) -> Optional[Path]:
        return self.song_metadata_loader.resolve_artifact_path(raw_path, meta_file)

    def _load_song_metadata(self, song_filename: str):
        return self.song_metadata_loader.load(song_filename)
