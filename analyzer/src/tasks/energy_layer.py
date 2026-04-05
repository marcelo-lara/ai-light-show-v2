from __future__ import annotations

from pathlib import Path
from typing import Any

from ..feature_layers.energy import build_energy_layer
from ..runtime.progress import ProgressCallback, emit_stage
from ..storage.song_meta import energy_layer_path
from .common import dump_json, merge_json_file, meta_file_path


def run(params: dict[str, Any], progress_callback: ProgressCallback | None = None) -> dict[str, Any]:
    song_path = Path(params["song_path"]).expanduser().resolve()
    meta_path = Path(params.get("meta_path", "/app/meta")).expanduser().resolve()
    emit_stage(progress_callback, "energy-layer", "Start", 1, 3)
    payload = build_energy_layer(song_path, meta_path)
    emit_stage(progress_callback, "energy-layer", "Build Layer", 2, 3)
    output_path = energy_layer_path(song_path, meta_path)
    dump_json(output_path, payload)
    merge_json_file(meta_file_path(song_path, meta_path), {"artifacts": {"layer_c_energy_file": str(output_path)}})
    emit_stage(progress_callback, "energy-layer", "Complete", 3, 3)
    return {"status": "completed", "layer_c_energy_file": str(output_path)}


TASK = {
    "value": "energy-layer",
    "label": "Build Energy Layer",
    "description": "Build the consolidated energy layer artifact from current analyzer feature outputs.",
    "params": ["song_path", "meta_path"],
    "runner": run,
}