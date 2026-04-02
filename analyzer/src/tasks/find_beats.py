from __future__ import annotations

from pathlib import Path
from typing import Any

from ..engines.find_beats import find_beats_and_downbeats
from ..moises import import_moises
from ..runtime.progress import ProgressCallback, emit_stage
from ..storage.song_meta import song_meta_dir
from .common import has_moises_mix_data, meta_file_path, normalize_analyzer_beats, warn, write_song_beats


def run(params: dict[str, Any], progress_callback: ProgressCallback | None = None) -> dict[str, Any] | None:
    song_path = Path(params["song_path"]).expanduser().resolve()
    meta_root = Path(params.get("meta_path", "/app/meta")).expanduser().resolve()
    print(f"Running beat finder for {song_path.name}")
    try:
        emit_stage(progress_callback, "beat-finder", "Start", 1, 4)
        song_meta_dir(song_path, meta_root).mkdir(parents=True, exist_ok=True)
        meta_file_path(song_path, meta_root)
        if has_moises_mix_data(song_path, meta_root):
            emit_stage(progress_callback, "beat-finder", "Import Moises Beats", 2, 4)
            print(f"Using Moises mix data for beats and chords: {song_path.name}")
            moises_beats = import_moises(song_path.stem, meta_path=meta_root)
            if moises_beats:
                emit_stage(progress_callback, "beat-finder", "Write Beats", 3, 4)
                beats_file = write_song_beats(song_path, meta_root, moises_beats, "moises")
                emit_stage(progress_callback, "beat-finder", "Complete", 4, 4)
                print("Beat import complete. Beats file:", beats_file)
                return {"method": "moises", "beat_count": len(moises_beats), "beats_file": str(beats_file)}
            warn("Moises mix data was present but unusable; falling back to analyzer beat finder")
        emit_stage(progress_callback, "beat-finder", "Find Beats", 2, 4)
        beat_data = find_beats_and_downbeats(song_path=song_path)
        emit_stage(progress_callback, "beat-finder", "Write Beats", 3, 4)
        beats_file = write_song_beats(song_path, meta_root, normalize_analyzer_beats(beat_data), "analyzer", beat_data)
        emit_stage(progress_callback, "beat-finder", "Complete", 4, 4)
        print("Beat finding complete. Beats file:", beats_file)
        return {**beat_data, "beats_file": str(beats_file)}
    except Exception as exc:
        emit_stage(progress_callback, "beat-finder", "Failed", 4, 4)
        warn(f"Beat finder failed: {exc}")
        return None


TASK = {
    "value": "beat-finder",
    "label": "Beat Finder",
    "description": "Detect beat and downbeat timing for the mix.",
    "params": ["song_path", "meta_path"],
    "runner": run,
}