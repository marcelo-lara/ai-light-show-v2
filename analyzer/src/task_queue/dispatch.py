from __future__ import annotations

from pathlib import Path
from typing import Any

from ..runtime.progress import ProgressCallback
from ..tasks.catalog import TASKS_BY_TYPE, list_task_types as list_catalog_task_types, run_registered_task

TASK_TYPES = frozenset(TASKS_BY_TYPE)


def list_task_types() -> list[dict[str, Any]]:
    return list_catalog_task_types()


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
    result = run_registered_task(task_type, params, progress_callback=progress_callback)
    return {
        "ok": result is not None,
        "task_type": task_type,
        "song": song_path.name,
        "params": _to_jsonable(params),
        "value": _to_jsonable(result),
    }
