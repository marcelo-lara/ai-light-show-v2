from pathlib import Path
from typing import Any, List, Optional
from models.song import Song
from ..constants import MAX_SONG_SECONDS

class StateCoreMetadataMixin:
    def _infer_song_length_seconds(self, song: Song) -> float:
        raw = song.meta.duration if song._meta else None
        if isinstance(raw, (int, float)) and raw > 0:
            return float(raw)

        max_t = 0.0
        if song.sections:
            for s in song.sections.sections:
                end_s = s.get("end_s")
                if end_s:
                    max_t = max(max_t, float(end_s))
                    
        if max_t <= 0:
            max_t = float(MAX_SONG_SECONDS)
        return min(float(MAX_SONG_SECONDS), max_t)

    def _resolve_analyzer_artifact_path(self, raw_path: Any, meta_file: Path) -> Optional[Path]:
        return None # Deprecated stub, handled through absolute /app/meta url payloads instead

    def _load_song_metadata(self, song_filename: str):
        # Now obsolete, song directly lazily loads it
        return None
