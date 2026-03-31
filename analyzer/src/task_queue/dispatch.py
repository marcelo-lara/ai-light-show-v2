from __future__ import annotations

from pathlib import Path
from typing import Any

import analyze_song

from ..progress import ProgressCallback

TASK_TYPES = {
    "split-stems",
    "beat-finder",
    "essentia-analysis",
    "find-song-features",
    "find_chords",
    "find_sections",
    "import-moises",
    "generate-md",
}


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    return value


def _song_path(params: dict[str, Any]) -> Path:
    song_path = params.get("song_path")
    if not song_path:
        raise ValueError("Missing required parameter: song_path")
    return Path(song_path)


def run_task(task_type: str, params: dict[str, Any], progress_callback: ProgressCallback | None = None) -> dict[str, Any]:
    if task_type not in TASK_TYPES:
        raise ValueError(f"Unsupported task_type: {task_type}")

    song_path = _song_path(params)
    meta_path = params.get("meta_path", analyze_song.META_PATH)

    if task_type == "split-stems":
        device = params.get("device") or analyze_song.autodetect_device()
        result = analyze_song.run_split_stems_for(song_path, device, meta_path=meta_path, progress_callback=progress_callback)
    elif task_type == "beat-finder":
        result = analyze_song.run_beat_finder_for(song_path, meta_path=meta_path, progress_callback=progress_callback)
    elif task_type == "essentia-analysis":
        result = analyze_song.run_essentia_analysis_for(song_path, meta_path=meta_path, progress_callback=progress_callback)
    elif task_type == "find-song-features":
        result = analyze_song.run_find_song_features_for(song_path, meta_path=meta_path, progress_callback=progress_callback)
    elif task_type == "find_chords":
        output_name = params.get("output_name", "beats.json")
        result = analyze_song.run_find_chords_for(song_path, meta_path=meta_path, output_name=output_name, progress_callback=progress_callback)
    elif task_type == "find_sections":
        output_name = params.get("output_name", "sections.json")
        result = analyze_song.run_find_sections_for(song_path, meta_path=meta_path, output_name=output_name, progress_callback=progress_callback)
    elif task_type == "import-moises":
        result = analyze_song.run_import_moises_for(song_path, meta_path=meta_path, progress_callback=progress_callback)
    else:
        result = analyze_song.run_generate_md_for(song_path, meta_path=meta_path, progress_callback=progress_callback)

    return {
        "ok": result is not None,
        "task_type": task_type,
        "song": song_path.name,
        "params": _to_jsonable(params),
        "value": _to_jsonable(result),
    }
