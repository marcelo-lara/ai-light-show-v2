from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple


SUPPORTED_TASK_TYPES = {
    "split-stems",
    "beat-finder",
    "essentia-analysis",
    "find-song-features",
    "import-moises",
    "generate-md",
}


def validate_task_type(payload: Dict[str, Any]) -> Tuple[str | None, Dict[str, Any] | None]:
    task_type = str(payload.get("task_type") or "").strip()
    if not task_type:
        return None, {"reason": "missing_task_type"}
    if task_type not in SUPPORTED_TASK_TYPES:
        return None, {"reason": "unsupported_task_type", "task_type": task_type}
    return task_type, None


def resolve_song_params(manager, payload: Dict[str, Any]) -> Tuple[dict[str, Any] | None, Dict[str, Any] | None]:
    filename = str(payload.get("filename") or getattr(manager.state_manager.current_song, "song_id", "") or "").strip()
    if not filename:
        return None, {"reason": "missing_filename"}

    available_songs = manager.song_service.list_songs()
    if filename not in available_songs:
        return None, {"reason": "unknown_song", "filename": filename, "songs": available_songs}

    song_path = Path(manager.song_service.songs_path) / f"{filename}.mp3"
    meta_path = Path(manager.song_service.meta_path)
    if not song_path.exists():
        return None, {"reason": "song_file_missing", "filename": filename, "song_path": str(song_path)}

    return {
        "filename": filename,
        "song_path": str(song_path),
        "meta_path": str(meta_path),
    }, None


def item_id_from_payload(payload: Dict[str, Any]) -> Tuple[str | None, Dict[str, Any] | None]:
    item_id = str(payload.get("item_id") or "").strip()
    if not item_id:
        return None, {"reason": "missing_item_id"}
    return item_id, None