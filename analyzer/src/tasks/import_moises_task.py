from __future__ import annotations

from pathlib import Path
from typing import Any

from ..moises import import_moises
from ..runtime.progress import ProgressCallback, emit_stage
from .common import meta_file_path, warn, write_song_beats


def run(params: dict[str, Any], progress_callback: ProgressCallback | None = None) -> dict[str, Any] | None:
    song_path = Path(params["song_path"]).expanduser().resolve()
    meta_root = Path(params.get("meta_path", "/app/meta")).expanduser().resolve()
    print(f"Running import moises for {song_path.name}")
    try:
        emit_stage(progress_callback, "import-moises", "Start", 1, 4)
        meta_file_path(song_path, meta_root)
        emit_stage(progress_callback, "import-moises", "Import Moises", 2, 4)
        moises_beats = import_moises(song_path.stem, meta_path=meta_root)
        if not moises_beats:
            warn(f"No usable Moises mix data found for {song_path.name}")
            return None
        emit_stage(progress_callback, "import-moises", "Write Beats", 3, 4)
        beats_file = write_song_beats(song_path, meta_root, moises_beats, "moises")
        emit_stage(progress_callback, "import-moises", "Complete", 4, 4)
        print("Moises import complete. Beats file:", beats_file)
        return {"method": "moises", "beat_count": len(moises_beats), "beats_file": str(beats_file)}
    except Exception as exc:
        emit_stage(progress_callback, "import-moises", "Failed", 4, 4)
        warn(f"Import moises failed: {exc}")
        return None


TASK = {
    "value": "import-moises",
    "label": "Import Moises",
    "description": "Import compatible Moises metadata into canonical analyzer files without modifying the Moises source files.",
    "params": ["song_path", "meta_path"],
    "runner": run,
}