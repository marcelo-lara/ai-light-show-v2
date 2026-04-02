from __future__ import annotations

from pathlib import Path
from typing import Any

from ..runtime.progress import ProgressCallback, emit_stage
from ..song_features import find_song_features
from .common import warn


def run(params: dict[str, Any], progress_callback: ProgressCallback | None = None) -> Path | None:
    song_path = Path(params["song_path"]).expanduser().resolve()
    meta_path = params.get("meta_path", "/app/meta")
    print(f"Finding song features for {song_path.name}")
    try:
        emit_stage(progress_callback, "find-song-features", "Start", 1, 3)
        emit_stage(progress_callback, "find-song-features", "Extract Features", 2, 3)
        output_path = find_song_features(song_path, meta_path=meta_path)
        if output_path is None:
            warn(f"Could not build song features for {song_path.stem}")
            return None
        emit_stage(progress_callback, "find-song-features", "Complete", 3, 3)
        print("Song feature generation complete. Output:", output_path)
        return output_path
    except Exception as exc:
        emit_stage(progress_callback, "find-song-features", "Failed", 3, 3)
        warn(f"Find song features failed: {exc}")
        return None


TASK = {
    "value": "find-song-features",
    "label": "Find Song Features",
    "description": "Synthesize section-level lighting features from analyzer artifacts.",
    "params": ["song_path", "meta_path"],
    "runner": run,
}