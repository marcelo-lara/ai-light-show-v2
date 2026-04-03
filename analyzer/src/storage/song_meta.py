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


def reference_dir(song_path: str | Path, meta_path: str | Path) -> Path:
    return song_meta_dir(song_path, meta_path) / "reference"


def inferred_dir(song_path: str | Path, meta_path: str | Path) -> Path:
    return song_meta_dir(song_path, meta_path) / "inferred"


def reference_beats_path(song_path: str | Path, meta_path: str | Path) -> Path:
    return reference_dir(song_path, meta_path) / "beats.json"


def inferred_beats_path(song_path: str | Path, meta_path: str | Path, model_name: str) -> Path:
    return inferred_dir(song_path, meta_path) / f"beats.{model_name}.json"


def info_path(song_path: str | Path, meta_path: str | Path) -> Path:
    return song_meta_dir(song_path, meta_path) / "info.json"


def load_song_info(song_path: str | Path, meta_path: str | Path) -> dict[str, Any]:
    path = info_path(song_path, meta_path)
    if not path.exists():
        return {}
    payload = load_json_file(path)
    return payload if isinstance(payload, dict) else {}


def _is_supported_beats_path(path: Path) -> bool:
    return path.parent.name in {"reference", "inferred"}


def _resolve_meta_path(path: Path, meta_path: str | Path) -> Path:
    if path.exists() or not path.is_absolute():
        return path
    try:
        relative = path.relative_to("/app/meta")
    except ValueError:
        return path
    return Path(meta_path).expanduser().resolve() / relative


def canonical_beats_path(song_path: str | Path, meta_path: str | Path) -> Path:
    info_payload = load_song_info(song_path, meta_path)
    beats_file = info_payload.get("beats_file")
    if isinstance(beats_file, str) and beats_file:
        beats_path = _resolve_meta_path(Path(beats_file), meta_path)
        if _is_supported_beats_path(beats_path):
            return beats_path
    artifacts = info_payload.get("artifacts")
    if isinstance(artifacts, dict):
        artifact_beats_file = artifacts.get("beats_file")
        if isinstance(artifact_beats_file, str) and artifact_beats_file:
            beats_path = _resolve_meta_path(Path(artifact_beats_file), meta_path)
            if _is_supported_beats_path(beats_path):
                return beats_path
    reference_path = reference_beats_path(song_path, meta_path)
    if reference_path.exists():
        return reference_path
    inferred_paths = sorted(inferred_dir(song_path, meta_path).glob("beats.*.json"))
    if inferred_paths:
        return inferred_paths[0]
    return reference_path


def initialize_song_info(song_path: str | Path, meta_path: str | Path, *, bpm: float | None = None, duration: float | None = None) -> Path:
    song_file = Path(song_path).expanduser().resolve()
    meta_dir = song_meta_dir(song_file, meta_path)
    meta_dir.mkdir(parents=True, exist_ok=True)
    path = info_path(song_file, meta_path)
    if path.exists():
        return path
    payload = {
        "song_name": song_file.stem,
        "song_path": str(song_file),
        "bpm": round(float(bpm), 3) if bpm is not None else 0.0,
        "duration": round(float(duration), 3) if duration is not None else 0.0,
        "artifacts": {},
    }
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