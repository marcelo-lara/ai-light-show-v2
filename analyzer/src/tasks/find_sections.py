from __future__ import annotations

from pathlib import Path
from typing import Any

from ..musical_structure import find_sections
from ..runtime.progress import ProgressCallback, emit_stage
from .common import merge_musical_structure_info, warn


def run(params: dict[str, Any], progress_callback: ProgressCallback | None = None) -> dict[str, Any] | None:
    song_path = Path(params["song_path"]).expanduser().resolve()
    meta_path = params.get("meta_path", "/app/meta")
    output_name = params.get("output_name", "sections.json")
    print(f"Finding sections for {song_path.name}")
    try:
        emit_stage(progress_callback, "find_sections", "Start", 1, 3)
        emit_stage(progress_callback, "find_sections", "Infer Sections", 2, 3)
        output = find_sections(song_path, meta_path=meta_path, output_name=output_name)
        if output is None:
            warn(f"Could not infer sections for {song_path.stem}")
            return None
        merge_musical_structure_info(song_path, meta_path, "sections", output, "sections_file")
        emit_stage(progress_callback, "find_sections", "Complete", 3, 3)
        print("Section inference complete. Output:", output["sections_file"])
        return output
    except Exception as exc:
        emit_stage(progress_callback, "find_sections", "Failed", 3, 3)
        warn(f"Find sections failed: {exc}")
        return None


TASK = {
    "value": "find_sections",
    "label": "Find Sections",
    "description": "Infer song section boundaries with the configured music models.",
    "params": ["song_path", "meta_path", "output_name"],
    "runner": run,
}