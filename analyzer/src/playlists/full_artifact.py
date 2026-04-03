from __future__ import annotations

from pathlib import Path
from typing import Any

from ..runtime.progress import ProgressCallback
from ..storage.song_meta import song_meta_dir
from ..tasks.catalog import run_registered_task
from ..tasks.common import autodetect_device, has_moises_mix_data

FULL_ARTIFACT_PLAYLIST_METADATA = {
    "value": "full-artifact",
    "label": "Full Artifact Playlist",
    "description": "Produce the canonical analyzer artifact set for one song through analyzer-owned task modules.",
    "params": [
        {"name": "song_path", "description": "Absolute or analyzer-visible path to the source song file.", "required": True},
        {"name": "meta_path", "description": "Analyzer meta root for generated artifacts.", "required": False, "default": "/app/meta"},
        {"name": "device", "description": "Optional override for the stem split device.", "required": False},
    ],
    "variants": [
        {"value": "full-artifact-analyzer", "description": "Analyzer-native path that computes beats and sections internally."},
        {"value": "full-artifact-moises", "description": "Moises-backed path that normalizes external Moises metadata without modifying moises/ inputs."},
    ],
    "produces": ["info.json", "beats.json", "sections.json", "hints.json", "features.json", "essentia artifacts", "stems", "song markdown summary"],
}


def list_playlists() -> list[dict[str, Any]]:
    return [dict(FULL_ARTIFACT_PLAYLIST_METADATA)]


def get_playlist(value: str) -> dict[str, Any] | None:
    if value != FULL_ARTIFACT_PLAYLIST_METADATA["value"]:
        return None
    return dict(FULL_ARTIFACT_PLAYLIST_METADATA)


def build_full_artifact_playlist(song_path: str | Path, meta_path: str | Path, device: str | None = None) -> dict[str, Any]:
    song_file = Path(song_path).expanduser().resolve()
    meta_root = Path(meta_path).expanduser().resolve()
    resolved_device = device or autodetect_device()
    uses_moises = has_moises_mix_data(song_file, meta_root)
    song_dir = song_meta_dir(song_file, meta_root)
    sections_file = song_dir / "sections.json"
    moises_segments_file = song_dir / "moises" / "segments.json"
    tasks = [
        {"task_type": "init-song", "params": {"song_path": str(song_file), "meta_path": str(meta_root)}},
        {"task_type": "split-stems", "params": {"song_path": str(song_file), "meta_path": str(meta_root), "device": resolved_device}},
    ]
    if uses_moises:
        tasks.append({"task_type": "import-moises", "params": {"song_path": str(song_file), "meta_path": str(meta_root)}})
        if not sections_file.exists() and not moises_segments_file.exists():
            tasks.append({"task_type": "find_sections", "params": {"song_path": str(song_file), "meta_path": str(meta_root), "output_name": "sections.json"}})
    else:
        tasks.extend(
            [
                {"task_type": "beat-finder", "params": {"song_path": str(song_file), "meta_path": str(meta_root)}},
                {"task_type": "find_sections", "params": {"song_path": str(song_file), "meta_path": str(meta_root), "output_name": "sections.json"}},
            ]
        )
    tasks.extend(
        [
            {"task_type": "essentia-analysis", "params": {"song_path": str(song_file), "meta_path": str(meta_root)}},
            {"task_type": "find-song-features", "params": {"song_path": str(song_file), "meta_path": str(meta_root)}},
            {"task_type": "generate-md", "params": {"song_path": str(song_file), "meta_path": str(meta_root)}},
        ]
    )
    return {"playlist": "full-artifact-moises" if uses_moises else "full-artifact-analyzer", "song": song_file.name, "uses_moises": uses_moises, "tasks": tasks}


def execute_full_artifact_playlist(song_path: str | Path, meta_path: str | Path, device: str | None = None, progress_callback: ProgressCallback | None = None) -> dict[str, Any]:
    playlist = build_full_artifact_playlist(song_path, meta_path, device=device)
    results: list[dict[str, Any]] = []
    status = "completed"
    for item in playlist["tasks"]:
        value = run_registered_task(item["task_type"], item["params"], progress_callback=progress_callback)
        ok = value is not None
        results.append({"task_type": item["task_type"], "ok": ok, "value": _to_jsonable(value)})
        if not ok:
            status = "failed"
            break
    return {**playlist, "status": status, "results": results}


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