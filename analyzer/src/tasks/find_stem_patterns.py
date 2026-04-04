from __future__ import annotations

from pathlib import Path
from typing import Any

from ..runtime.progress import ProgressCallback, emit_stage
from ..song_features.stem_patterns import build_stem_patterns
from ..storage.song_meta import load_json_file, song_meta_dir
from .common import dump_json, merge_json_file, meta_file_path, warn


def run(params: dict[str, Any], progress_callback: ProgressCallback | None = None) -> dict[str, Any]:
    song_path = Path(params["song_path"]).expanduser().resolve()
    meta_path = Path(params.get("meta_path", "/app/meta")).expanduser().resolve()
    song_dir = song_meta_dir(song_path, meta_path)
    chord_patterns_file = song_dir / "chord_patterns.json"
    print(f"Finding stem patterns for {song_path.name}")
    emit_stage(progress_callback, "find-stem-patterns", "Start", 1, 3)
    emit_stage(progress_callback, "find-stem-patterns", "Match Stem Windows", 2, 3)
    chord_patterns = load_json_file(chord_patterns_file) if chord_patterns_file.exists() else None
    payload = build_stem_patterns(song_dir, chord_patterns)
    if payload is None:
        warn(f"Find stem patterns skipped: no repeating stem patterns for {song_path.stem}")
        emit_stage(progress_callback, "find-stem-patterns", "Skipped", 3, 3)
        return {"status": "skipped", "reason": "no_stem_patterns", "chord_patterns_file": str(chord_patterns_file)}
    output_path = song_dir / "stem_patterns.json"
    dump_json(output_path, payload)
    merge_json_file(meta_file_path(song_path, meta_path), {"artifacts": {"stem_patterns_file": str(output_path)}})
    emit_stage(progress_callback, "find-stem-patterns", "Complete", 3, 3)
    print("Stem pattern extraction complete. Output:", output_path)
    return {"status": "completed", "stem_patterns_file": str(output_path), "pattern_count": payload["pattern_count"], "alignment": payload["settings"]["alignment"]}


TASK = {
    "value": "find-stem-patterns",
    "label": "Find Stem Patterns",
    "description": "Group repeating stem loudness and envelope profiles, trying chord pattern windows first and falling back to signal windows.",
    "params": ["song_path", "meta_path"],
    "runner": run,
}