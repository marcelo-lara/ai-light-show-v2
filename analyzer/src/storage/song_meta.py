from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json_file(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_list_file(path: Path) -> list[Any]:
    if not path.exists():
        return []
    payload = load_json_file(path)
    return payload if isinstance(payload, list) else []


def song_name(song_path: str | Path) -> str:
    return Path(song_path).expanduser().resolve().stem


def song_meta_dir(song_path: str | Path, meta_path: str | Path) -> Path:
    return Path(meta_path).expanduser().resolve() / song_name(song_path)


def info_path(song_path: str | Path, meta_path: str | Path) -> Path:
    return song_meta_dir(song_path, meta_path) / "info.json"


def initialize_song_info(song_path: str | Path, meta_path: str | Path) -> Path:
    song_file = Path(song_path).expanduser().resolve()
    meta_dir = song_meta_dir(song_file, meta_path)
    meta_dir.mkdir(parents=True, exist_ok=True)
    path = info_path(song_file, meta_path)
    if path.exists():
        return path
    payload = {"song_name": song_file.stem, "song_path": str(song_file), "artifacts": {}}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def load_sections(meta_dir: Path) -> list[dict[str, Any]]:
    sections = load_list_file(meta_dir / "sections.json")
    normalized: list[dict[str, Any]] = []
    for index, section in enumerate(sections, start=1):
        if not isinstance(section, dict):
            continue
        start_value = float(section.get("start_s", section.get("start", 0.0)) or 0.0)
        end_value = float(section.get("end_s", section.get("end", start_value)) or start_value)
        normalized.append({"name": str(section.get("name") or section.get("label") or f"Section {index}"), "start_s": round(start_value, 3), "end_s": round(max(end_value, start_value), 3)})
    return normalized