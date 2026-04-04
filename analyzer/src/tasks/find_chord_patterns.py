from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..musical_structure.chord_patterns import find_chord_patterns
from ..runtime.progress import ProgressCallback, emit_stage
from ..storage.song_meta import canonical_beats_path, song_meta_dir
from .common import dump_json, merge_json_file, meta_file_path, warn


def run(params: dict[str, Any], progress_callback: ProgressCallback | None = None) -> dict[str, Any]:
    song_path = Path(params["song_path"]).expanduser().resolve()
    meta_path = Path(params.get("meta_path", "/app/meta")).expanduser().resolve()
    beats_file = canonical_beats_path(song_path, meta_path)
    print(f"Finding chord patterns for {song_path.name}")
    emit_stage(progress_callback, "find-chord-patterns", "Start", 1, 3)
    rows = [] if not beats_file.exists() else json.loads(beats_file.read_text(encoding="utf-8"))
    beats = [row for row in rows if isinstance(row, dict)]
    if not beats:
        warn(f"Find chord patterns skipped: missing canonical beats for {song_path.stem}")
        emit_stage(progress_callback, "find-chord-patterns", "Skipped", 3, 3)
        return {"status": "skipped", "reason": "missing_beats", "beats_file": str(beats_file)}
    emit_stage(progress_callback, "find-chord-patterns", "Match Patterns", 2, 3)
    payload = find_chord_patterns(beats, beats_file=str(beats_file))
    if payload is None:
        warn(f"Find chord patterns skipped: no repeating chord patterns for {song_path.stem}")
        emit_stage(progress_callback, "find-chord-patterns", "Skipped", 3, 3)
        return {"status": "skipped", "reason": "no_patterns", "beats_file": str(beats_file)}
    output_path = song_meta_dir(song_path, meta_path) / "chord_patterns.json"
    dump_json(output_path, payload)
    merge_json_file(meta_file_path(song_path, meta_path), {"artifacts": {"chord_patterns_file": str(output_path)}})
    emit_stage(progress_callback, "find-chord-patterns", "Complete", 3, 3)
    print("Chord pattern extraction complete. Output:", output_path)
    return {"status": "completed", "beats_file": str(beats_file), "chord_patterns_file": str(output_path), "pattern_count": payload["pattern_count"]}


TASK = {
    "value": "find-chord-patterns",
    "label": "Find Chord Patterns",
    "description": "Group repeating chord progressions from canonical beat metadata.",
    "params": ["song_path", "meta_path"],
    "runner": run,
}