from __future__ import annotations

from pathlib import Path
from typing import Any

from ..runtime.progress import ProgressCallback, emit_stage
from ..report_tool.generate_md import generate_md_file
from .common import warn


def run(params: dict[str, Any], progress_callback: ProgressCallback | None = None) -> Path | None:
    song_path = Path(params["song_path"]).expanduser().resolve()
    meta_path = params.get("meta_path", "/app/meta")
    print(f"Generating lighting score for {song_path.name}")
    try:
        emit_stage(progress_callback, "generate-md", "Start", 1, 3)
        emit_stage(progress_callback, "generate-md", "Generate Lighting Score", 2, 3)
        output_path = generate_md_file(song_path, meta_path=meta_path)
        if output_path is None:
            warn(f"No merged music feature layers found for {song_path.stem}")
            return None
        emit_stage(progress_callback, "generate-md", "Complete", 3, 3)
        print("Lighting score generation complete. Output:", output_path)
        return output_path
    except Exception as exc:
        emit_stage(progress_callback, "generate-md", "Failed", 3, 3)
        warn(f"Generate markdown failed: {exc}")
        return None


TASK = {
    "value": "generate-md",
    "label": "Generate Lighting Score",
    "description": "Render the canonical lighting score markdown from the merged analyzer IR.",
    "params": ["song_path", "meta_path"],
    "runner": run,
}