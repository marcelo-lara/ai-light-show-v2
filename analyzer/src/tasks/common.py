from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import librosa

from ..storage.song_meta import inferred_beats_path, initialize_song_info, load_list_file, reference_beats_path, song_meta_dir


def warn(message: str) -> None:
    print(f"WARNING: {message}")


def autodetect_device() -> str:
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception as exc:
        warn(f"Could not detect CUDA availability ({exc}); using cpu")
        return "cpu"


def dump_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_round_floats(payload), indent=2), encoding="utf-8")


def merge_json_file(path: Path, updates: dict[str, Any]) -> None:
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {}
    _deep_update(data, updates)
    dump_json(path, data)


def meta_file_path(song_path: str | Path, meta_path: str | Path) -> Path:
    return initialize_song_info(song_path, meta_path)


def musical_structure_payload(output: dict[str, Any], artifact_key: str) -> dict[str, Any]:
    return {
        "method": output.get("method"),
        "confidence": output.get("confidence"),
        "attempts": output.get("attempts"),
        "inputs": output.get("inputs"),
        "candidates": output.get("candidates"),
        "artifact": output.get(artifact_key),
    }


def merge_musical_structure_info(song_path: str | Path, meta_path: str | Path, key: str, output: dict[str, Any], artifact_key: str) -> None:
    merge_json_file(
        meta_file_path(song_path, meta_path),
        {"musical_structure_inference": {key: musical_structure_payload(output, artifact_key)}},
    )


def has_moises_mix_data(song_path: str | Path, meta_path: str | Path) -> bool:
    moises_dir = song_meta_dir(song_path, meta_path) / "moises"
    return bool(load_list_file(moises_dir / "beats.json") or load_list_file(moises_dir / "chords.json"))


def normalize_analyzer_beats(beat_data: dict[str, Any]) -> list[dict[str, Any]]:
    beats = [float(time) for time in beat_data.get("beats", [])]
    downbeats = [float(time) for time in beat_data.get("downbeats", [])]
    if not beats:
        return []
    first_downbeat_index = 0
    if downbeats:
        first_downbeat = downbeats[0]
        first_downbeat_index = min(range(len(beats)), key=lambda index: abs(beats[index] - first_downbeat))
    return [
        {
            "time": round(time_value, 3),
            "beat": ((index - first_downbeat_index) % 4) + 1,
            "bar": ((index - first_downbeat_index) // 4) + 1,
            "bass": None,
            "chord": None,
        }
        for index, time_value in enumerate(beats)
    ]


def write_song_beats(song_path: Path, meta_root: Path, beats: list[dict[str, Any]], source: str, beat_data: dict[str, Any] | None = None) -> Path:
    default_model = "librosa" if source == "analyzer" else source
    model_name = str((beat_data or {}).get("method") or default_model).replace(" ", "_")
    reference_file = reference_beats_path(song_path, meta_root)
    if source == "moises":
        beats_file = reference_file
    else:
        beats_file = inferred_beats_path(song_path, meta_root, model_name)
    beats_file.parent.mkdir(parents=True, exist_ok=True)
    annotated_beats = [{**beat_event, "type": "downbeat" if beat_event.get("beat") == 1 else "beat"} for beat_event in beats]
    dump_json(beats_file, annotated_beats)
    reference_exists = reference_file.exists()
    canonical_file = reference_file if source == "moises" or reference_exists else beats_file
    artifacts: dict[str, Any] = {"beats_file": str(canonical_file)}
    if source == "moises":
        artifacts["reference_beats_file"] = str(beats_file)
    else:
        artifacts["inferred_beats_files"] = {model_name: str(beats_file)}
    moises_chords_file = song_meta_dir(song_path, meta_root) / "moises" / "chords.json"
    if source == "moises" and moises_chords_file.exists():
        artifacts["chords_file"] = str(moises_chords_file)
    info_updates: dict[str, Any] = {
        "song_name": song_path.stem,
        "song_path": str(song_path),
        "beats_file": str(canonical_file),
        "beats_source": "reference" if reference_exists or source == "moises" else source,
        "beat_tracking": {
            "method": source,
            "tempo_bpm": (beat_data or {}).get("tempo_bpm"),
            "sample_rate": (beat_data or {}).get("sample_rate"),
            "beat_count": len(annotated_beats),
            "downbeat_count": sum(1 for beat in annotated_beats if beat.get("beat") == 1),
            "beat_strength_mean": (beat_data or {}).get("beat_strength_mean"),
            "downbeat_strength_mean": (beat_data or {}).get("downbeat_strength_mean"),
            "meter_assumption": (beat_data or {}).get("meter_assumption", "4/4"),
        },
        "artifacts": artifacts,
    }
    tempo_bpm = (beat_data or {}).get("tempo_bpm")
    if tempo_bpm is not None:
        info_updates["bpm"] = tempo_bpm
    duration = (beat_data or {}).get("duration")
    if duration is not None:
        info_updates["duration"] = duration
    merge_json_file(
        meta_file_path(song_path, meta_root),
        info_updates,
    )
    return beats_file


def read_sample_rate(audio_path: str | Path) -> int | None:
    try:
        return int(librosa.get_samplerate(str(audio_path)))
    except Exception as exc:
        warn(f"Could not read sample rate for {audio_path}: {exc}")
        return None


def build_essentia_manifest(essentia_dir: Path, part_artifacts: dict[str, dict[str, Any]], features: tuple[str, ...], *, include_plots: bool = False) -> dict[str, Any]:
    manifest: dict[str, Any] = {}
    for part_name, artifacts in part_artifacts.items():
        manifest[part_name] = {}
        for artifact_name in artifacts:
            file_stem = artifact_name if part_name == "mix" else f"{part_name}_{artifact_name}"
            payload = {"json": str(essentia_dir / f"{file_stem}.json")}
            if include_plots:
                payload["svg"] = str(essentia_dir / f"{file_stem}.svg")
            manifest[part_name][artifact_name] = payload
    return manifest


def _round_floats(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 3)
    if isinstance(value, dict):
        return {key: _round_floats(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_round_floats(item) for item in value]
    if isinstance(value, tuple):
        return [_round_floats(item) for item in value]
    return value


def _deep_update(base: dict[str, Any], updates: dict[str, Any]) -> None:
    for key, value in updates.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_update(base[key], value)
        else:
            base[key] = value