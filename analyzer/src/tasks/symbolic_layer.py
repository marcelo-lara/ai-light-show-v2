from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..engines.basic_pitch import transcribe_sources
from ..feature_layers.symbolic import build_symbolic_layer
from ..runtime.progress import ProgressCallback, emit_stage
from ..storage.song_meta import symbolic_layer_path
from .common import dump_json, merge_json_file, meta_file_path


def run(params: dict[str, Any], progress_callback: ProgressCallback | None = None) -> dict[str, Any]:
    song_path = Path(params["song_path"]).expanduser().resolve()
    meta_path = Path(params.get("meta_path", "/app/meta")).expanduser().resolve()
    emit_stage(progress_callback, "symbolic-layer", "Start", 1, 4)
    sources = _symbolic_sources(song_path, meta_path)
    notes = transcribe_sources(sources)
    emit_stage(progress_callback, "symbolic-layer", "Transcribe Notes", 2, 4)
    payload = build_symbolic_layer(song_path, meta_path, notes=notes, stems_used=list(sources.keys()))
    emit_stage(progress_callback, "symbolic-layer", "Build Layer", 3, 4)
    output_path = symbolic_layer_path(song_path, meta_path)
    dump_json(output_path, payload)
    merge_json_file(meta_file_path(song_path, meta_path), {"artifacts": {"layer_b_symbolic_file": str(output_path)}})
    emit_stage(progress_callback, "symbolic-layer", "Complete", 4, 4)
    return {"status": "completed", "layer_b_symbolic_file": str(output_path), "note_count": len(payload["note_events"])}


def _symbolic_sources(song_path: Path, meta_path: Path) -> dict[str, Path]:
    meta_file = meta_path / song_path.stem / "info.json"
    if not meta_file.exists():
        return {"mix": song_path}
    payload = json.loads(meta_file.read_text(encoding="utf-8"))
    stems = payload.get("stems") if isinstance(payload.get("stems"), list) else []
    discovered = {Path(stem).stem: Path(stem) for stem in stems if isinstance(stem, str)}
    sources: dict[str, Path] = {}
    if discovered.get("other") and discovered["other"].exists():
        sources["harmonic"] = discovered["other"]
    if discovered.get("bass") and discovered["bass"].exists():
        sources["bass"] = discovered["bass"]
    return sources or {"mix": song_path}


TASK = {
    "value": "symbolic-layer",
    "label": "Build Symbolic Layer",
    "description": "Build the consolidated symbolic layer artifact using Basic Pitch on harmonic and bass sources.",
    "params": ["song_path", "meta_path"],
    "runner": run,
}