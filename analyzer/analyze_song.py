from __future__ import annotations

import json
from pathlib import Path

from src.beat_finder import find_beats_and_downbeats
from src.split_stems import MODEL_NAME, TEMP_FILES_FOLDER, split_stems

METADATA_PATH = "/app/meta"

# 1. Select song
SONG_PATH = "/app/songs/Yonaka - Seize the Power.mp3"

def _metadata_file_path(song_path: str | Path, metadata_path: str | Path) -> Path:
    song_name = Path(song_path).expanduser().resolve().stem
    return Path(metadata_path).expanduser().resolve() / f"{song_name}.json"


def _merge_json_file(path: Path, updates: dict) -> None:
    payload: dict = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    payload.update(updates)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def analyze_song(
    song_path: str | Path = SONG_PATH,
    metadata_path: str | Path = METADATA_PATH,
    stems_output_dir: str | Path = TEMP_FILES_FOLDER,
    device: str = "cuda",
) -> dict:
    """Run the analyzer pipeline for one song.

    Current pipeline:
    1) Split stems with Demucs.
    2) Placeholder for beat finding.
    """
    metadata_dir = Path(metadata_path).expanduser().resolve()
    metadata_dir.mkdir(parents=True, exist_ok=True)

    stems_dir = split_stems(
        song_path=song_path,
        output_dir=stems_output_dir,
        model=MODEL_NAME,
        device=device,
        metadata_dir=metadata_dir,
    )

    # 2. Find beats and downbeats (librosa only)
    beat_data = find_beats_and_downbeats(song_path=song_path)
    metadata_file = _metadata_file_path(song_path, metadata_dir)
    _merge_json_file(
        metadata_file,
        {
            "beat_tracking": beat_data,
        },
    )

    return {
        "song_path": str(Path(song_path).expanduser().resolve()),
        "metadata_path": str(metadata_dir),
        "metadata_file": str(metadata_file),
        "stems_dir": str(stems_dir),
        "beat_tracking_method": beat_data.get("method"),
    }


def main() -> int:
    result = analyze_song()
    print("Analyze complete:", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
