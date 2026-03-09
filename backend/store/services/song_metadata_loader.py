import contextlib
import json
from pathlib import Path
from typing import Any, List, Optional

from models.song import SongMetadata

MAX_SONG_SECONDS = 6 * 60


class SongMetadataLoader:
    def __init__(self, meta_path: Path):
        self.meta_path = meta_path

    def meta_candidates(self, song_filename: str) -> List[Path]:
        return [
            self.meta_path / f"{song_filename}.json",
            self.meta_path / song_filename / f"{song_filename}.json",
            self.meta_path / song_filename / "meta.json",
        ]

    def resolve_artifact_path(self, raw_path: Any, meta_file: Path) -> Optional[Path]:
        if not raw_path:
            return None

        text = str(raw_path).strip()
        if not text:
            return None

        candidate = Path(text)
        if candidate.exists():
            return candidate

        if candidate.is_absolute():
            with contextlib.suppress(ValueError):
                parts = candidate.parts
                if "meta" in parts:
                    meta_idx = parts.index("meta")
                    relative = Path(*parts[meta_idx + 1:])
                    mapped = self.meta_path / relative
                    if mapped.exists():
                        return mapped

        relative_candidate = meta_file.parent / text
        if relative_candidate.exists():
            return relative_candidate

        return None

    def load(self, song_filename: str) -> SongMetadata:
        meta_file: Optional[Path] = None
        for candidate in self.meta_candidates(song_filename):
            if candidate.exists():
                meta_file = candidate
                break

        if not meta_file:
            return SongMetadata(filename=song_filename, parts={}, hints={}, drums={})

        with open(meta_file, "r") as handle:
            meta_data = json.load(handle)

        if not isinstance(meta_data, dict):
            return SongMetadata(filename=song_filename, parts={}, hints={}, drums={})

        if "filename" not in meta_data:
            meta_data["filename"] = song_filename

        metadata = SongMetadata(**meta_data)

        beat_tracking = meta_data.get("beat_tracking") or {}
        tempo_bpm = beat_tracking.get("tempo_bpm")

        beats: List[float] = []
        downbeats: List[float] = []

        artifacts = meta_data.get("artifacts") or {}
        beats_path = self.resolve_artifact_path(artifacts.get("beats_file"), meta_file)
        if not beats_path:
            fallback = meta_file.parent / "beats.json"
            beats_path = fallback if fallback.exists() else None

        if beats_path:
            with contextlib.suppress(OSError, ValueError, TypeError):
                with open(beats_path, "r") as handle:
                    beats_data = json.load(handle)
                beats = [float(value) for value in (beats_data.get("beats") or [])]
                downbeats = [float(value) for value in (beats_data.get("downbeats") or [])]

        if not downbeats and beats:
            downbeats = [beats[idx] for idx in range(0, len(beats), 4)]

        hints = dict(metadata.hints or {})
        drums = dict(metadata.drums or {})

        existing_hint_beats = hints.get("beats")
        existing_hint_downbeats = hints.get("downbeats")
        existing_drum_beats = drums.get("beats")
        existing_drum_downbeats = drums.get("downbeats")

        if beats and not (isinstance(existing_hint_beats, list) and len(existing_hint_beats) > 0):
            hints["beats"] = beats
        if downbeats and not (isinstance(existing_hint_downbeats, list) and len(existing_hint_downbeats) > 0):
            hints["downbeats"] = downbeats
        if beats and not (isinstance(existing_drum_beats, list) and len(existing_drum_beats) > 0):
            drums["beats"] = beats
        if downbeats and not (isinstance(existing_drum_downbeats, list) and len(existing_drum_downbeats) > 0):
            drums["downbeats"] = downbeats

        if metadata.bpm is None and isinstance(tempo_bpm, (int, float)):
            metadata.bpm = float(tempo_bpm)

        if metadata.length is None:
            if beats:
                metadata.length = float(max(beats))
            elif downbeats:
                metadata.length = float(max(downbeats))
            else:
                metadata.length = float(MAX_SONG_SECONDS)

        metadata.hints = hints
        metadata.drums = drums
        return metadata
