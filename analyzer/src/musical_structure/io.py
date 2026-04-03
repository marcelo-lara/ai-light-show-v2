from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.storage.song_meta import canonical_beats_path, inferred_dir, load_list_file, song_meta_dir

TIME_KEYS = {"time", "start", "end"}


def round_payload(value: Any, *, key: str | None = None) -> Any:
    if isinstance(value, float):
        return round(value, 3 if key in TIME_KEYS else 4)
    if isinstance(value, dict):
        return {child_key: round_payload(item, key=child_key) for child_key, item in value.items()}
    if isinstance(value, list):
        return [round_payload(item, key=key) for item in value]
    return value


def dump_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(round_payload(payload), indent=2), encoding="utf-8")


def meta_dir(song_path: str | Path, meta_path: str | Path) -> Path:
    path = song_meta_dir(song_path, meta_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def beats_path(song_path: str | Path, meta_path: str | Path, output_name: str = "beats.json") -> Path:
    if output_name == "beats.json":
        return canonical_beats_path(song_path, meta_path)
    path = inferred_dir(song_path, meta_path) / output_name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def sections_path(song_path: str | Path, meta_path: str | Path, output_name: str = "sections.json") -> Path:
    return meta_dir(song_path, meta_path) / output_name


def load_beats(song_path: str | Path, meta_path: str | Path, file_name: str = "beats.json") -> list[dict[str, Any]]:
    return [row for row in load_list_file(beats_path(song_path, meta_path, file_name)) if isinstance(row, dict)]


def load_sections(song_path: str | Path, meta_path: str | Path, file_name: str = "sections.json") -> list[dict[str, Any]]:
    return [row for row in load_list_file(sections_path(song_path, meta_path, file_name)) if isinstance(row, dict)]


def bass_stem_path(song_path: str | Path, temp_files_root: str | Path) -> Path:
    return Path(temp_files_root).expanduser().resolve() / "htdemucs" / Path(song_path).stem / "bass.wav"