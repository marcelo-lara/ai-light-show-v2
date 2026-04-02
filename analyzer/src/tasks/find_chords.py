from __future__ import annotations

from pathlib import Path
from typing import Any

from ..musical_structure import find_chords
from ..engines.split_stems import TEMP_FILES_FOLDER
from ..runtime.progress import ProgressCallback, emit_stage
from .common import merge_json_file, merge_musical_structure_info, meta_file_path, warn


def run(params: dict[str, Any], progress_callback: ProgressCallback | None = None) -> dict[str, Any] | None:
    song_path = Path(params["song_path"]).expanduser().resolve()
    meta_path = params.get("meta_path", "/app/meta")
    output_name = params.get("output_name", "beats.json")
    print(f"Finding chords for {song_path.name}")
    try:
        emit_stage(progress_callback, "find_chords", "Start", 1, 3)
        emit_stage(progress_callback, "find_chords", "Infer Chords", 2, 3)
        output = find_chords(song_path, meta_path=meta_path, temp_files_root=TEMP_FILES_FOLDER, output_name=output_name)
        if output is None:
            warn(f"Could not infer chords for {song_path.stem}")
            return None
        merge_musical_structure_info(song_path, meta_path, "chords", output, "beats_file")
        if output_name == "beats.json":
            merge_json_file(meta_file_path(song_path, meta_path), {"artifacts": {"beats_file": output["beats_file"]}, "musical_structure_inference": {"chords": {"bass_confidence": output.get("bass_confidence")}}})
        emit_stage(progress_callback, "find_chords", "Complete", 3, 3)
        print("Chord inference complete. Output:", output["beats_file"])
        return output
    except Exception as exc:
        emit_stage(progress_callback, "find_chords", "Failed", 3, 3)
        warn(f"Find chords failed: {exc}")
        return None


TASK = {
    "value": "find_chords",
    "label": "Find Chords",
    "description": "Infer beat-aligned chord labels with the configured music models.",
    "params": ["song_path", "meta_path", "output_name"],
    "runner": run,
}