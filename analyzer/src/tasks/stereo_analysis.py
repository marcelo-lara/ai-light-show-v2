from __future__ import annotations

from pathlib import Path
from typing import Any

from ..runtime.progress import ProgressCallback, emit_stage
from ..song_features import analyze_stereo
from .common import warn


def run(params: dict[str, Any], progress_callback: ProgressCallback | None = None) -> dict[str, Any] | None:
    song_path = Path(params["song_path"]).expanduser().resolve()
    meta_path = params.get("meta_path", "/app/meta")
    print(f"Running stereo analysis for {song_path.name}")
    try:
        emit_stage(progress_callback, "stereo-analysis", "Start", 1, 3)
        emit_stage(progress_callback, "stereo-analysis", "Analyze Stereo", 2, 3)
        payload = analyze_stereo(song_path, meta_path=meta_path)
        if payload is None:
            warn(f"Stereo analysis skipped: missing features.json or info.json for {song_path.stem}")
            emit_stage(progress_callback, "stereo-analysis", "Skipped", 3, 3)
            return None
        emit_stage(progress_callback, "stereo-analysis", "Complete", 3, 3)
        return {
            "status": "completed",
            "event_count": payload["summary"]["event_count"],
            "stereo_source_count": payload["summary"]["stereo_source_count"],
        }
    except Exception as exc:
        emit_stage(progress_callback, "stereo-analysis", "Failed", 3, 3)
        warn(f"Stereo analysis failed: {exc}")
        return None


TASK = {
    "value": "stereo-analysis",
    "label": "Stereo Analysis",
    "description": "Annotate only notable stereo differences for the mix and available stems.",
    "params": ["song_path", "meta_path"],
    "runner": run,
}