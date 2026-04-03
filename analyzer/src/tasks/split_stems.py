from __future__ import annotations

from pathlib import Path
from typing import Any

from ..engines.split_stems import MODEL_NAME, TEMP_FILES_FOLDER, split_stems
from ..runtime.progress import ProgressCallback, emit_stage
from ..storage.song_meta import song_meta_dir
from .common import autodetect_device, merge_json_file, meta_file_path, warn


def run(params: dict[str, Any], progress_callback: ProgressCallback | None = None) -> Path | None:
    song_path = Path(params["song_path"]).expanduser().resolve()
    meta_root = Path(params.get("meta_path", "/app/meta")).expanduser().resolve()
    device = params.get("device") or autodetect_device()
    print(f"Starting split stems for {song_path.name} on device={device}")
    try:
        emit_stage(progress_callback, "split-stems", "Start", 1, 4)
        song_dir = song_meta_dir(song_path, meta_root)
        song_dir.mkdir(parents=True, exist_ok=True)
        meta_file = meta_file_path(song_path, meta_root)
        emit_stage(progress_callback, "split-stems", "Split Stems", 2, 4)
        stems_dir, stem_files = split_stems(song_path=song_path, output_dir=TEMP_FILES_FOLDER, model=MODEL_NAME, device=device, meta_dir=song_dir)
        emit_stage(progress_callback, "split-stems", "Write Metadata", 3, 4)
        merge_json_file(
            meta_file,
            {"song_name": song_path.stem, "song_path": str(song_path), "model": MODEL_NAME, "device": device, "stems_dir": str(stems_dir), "stems": stem_files},
        )
        emit_stage(progress_callback, "split-stems", "Complete", 4, 4)
        print("Split stems complete. Output:", stems_dir)
        return Path(stems_dir)
    except Exception as exc:
        emit_stage(progress_callback, "split-stems", "Failed", 4, 4)
        warn(f"split_stems failed: {exc}")
        return None


TASK = {
    "value": "split-stems",
    "label": "Split Stems",
    "description": "Extract instrument stems from the song audio.",
    "params": ["song_path", "meta_path", "device"],
    "runner": run,
}