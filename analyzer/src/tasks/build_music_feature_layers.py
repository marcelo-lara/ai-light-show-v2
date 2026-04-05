from __future__ import annotations

from pathlib import Path
from typing import Any

from ..feature_layers.ir import build_music_feature_layers
from ..runtime.progress import ProgressCallback, emit_stage
from ..storage.song_meta import energy_layer_path, harmonic_layer_path, load_json_file, music_feature_layers_path, symbolic_layer_path
from .common import dump_json, merge_json_file, meta_file_path


def run(params: dict[str, Any], progress_callback: ProgressCallback | None = None) -> dict[str, Any]:
    song_path = Path(params["song_path"]).expanduser().resolve()
    meta_path = Path(params.get("meta_path", "/app/meta")).expanduser().resolve()
    emit_stage(progress_callback, "build-music-feature-layers", "Start", 1, 3)
    harmonic = _load(harmonic_layer_path(song_path, meta_path))
    symbolic = _load(symbolic_layer_path(song_path, meta_path))
    energy = _load(energy_layer_path(song_path, meta_path))
    payload = build_music_feature_layers(song_path, meta_path, harmonic, symbolic, energy)
    emit_stage(progress_callback, "build-music-feature-layers", "Merge Layers", 2, 3)
    output_path = music_feature_layers_path(song_path, meta_path)
    dump_json(output_path, payload)
    merge_json_file(meta_file_path(song_path, meta_path), {"artifacts": {"music_feature_layers_file": str(output_path)}})
    emit_stage(progress_callback, "build-music-feature-layers", "Complete", 3, 3)
    return {"status": "completed", "music_feature_layers_file": str(output_path)}


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = load_json_file(path)
    return payload if isinstance(payload, dict) else {}


TASK = {
    "value": "build-music-feature-layers",
    "label": "Build Music Feature Layers",
    "description": "Merge harmonic, symbolic, and energy layers into one LLM-ready analyzer IR.",
    "params": ["song_path", "meta_path"],
    "runner": run,
}