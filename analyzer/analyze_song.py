from __future__ import annotations

import json
from pathlib import Path

from src.beat_finder import find_beats_and_downbeats
from src.split_stems import MODEL_NAME, TEMP_FILES_FOLDER, split_stems

META_PATH = "/app/meta"

# 1. Select song
SONG_PATH = "/app/songs/Yonaka - Seize the Power.mp3"


def _song_name(song_path: str | Path) -> str:
    return Path(song_path).expanduser().resolve().stem


def _song_meta_dir(song_path: str | Path, meta_path: str | Path) -> Path:
    return Path(meta_path).expanduser().resolve() / _song_name(song_path)


def _meta_file_path(song_path: str | Path, meta_path: str | Path) -> Path:
    return _song_meta_dir(song_path, meta_path) / f"{_song_name(song_path)}.json"


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
    meta_path: str | Path = META_PATH,
    stems_output_dir: str | Path = TEMP_FILES_FOLDER,
    device: str = "cuda",
) -> dict:
    """Run the analyzer pipeline for one song.

    Current pipeline:
    1) Split stems with Demucs.
    2) Find beats/downbeats and write beat artifacts.
    """
    song_path = Path(song_path).expanduser().resolve()
    meta_root = Path(meta_path).expanduser().resolve()
    song_meta_dir = _song_meta_dir(song_path, meta_root)
    song_meta_dir.mkdir(parents=True, exist_ok=True)

    stems_dir = split_stems(
        song_path=song_path,
        output_dir=stems_output_dir,
        model=MODEL_NAME,
        device=device,
        meta_dir=song_meta_dir,
    )

    # 2. Find beats and downbeats (librosa only)
    beat_data = find_beats_and_downbeats(song_path=song_path)

    beats_file = song_meta_dir / "beats.json"
    with open(beats_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "beats": beat_data.get("beats", []),
                "downbeats": beat_data.get("downbeats", []),
            },
            f,
            indent=2,
        )

    meta_file = _meta_file_path(song_path, meta_root)
    _merge_json_file(
        meta_file,
        {
            "song_name": song_path.stem,
            "song_path": str(song_path),
            "beat_tracking": {
                "method": beat_data.get("method"),
                "tempo_bpm": beat_data.get("tempo_bpm"),
                "sample_rate": beat_data.get("sample_rate"),
                "beat_count": beat_data.get("beat_count"),
                "downbeat_count": beat_data.get("downbeat_count"),
                "beat_strength_mean": beat_data.get("beat_strength_mean"),
                "downbeat_strength_mean": beat_data.get("downbeat_strength_mean"),
                "meter_assumption": beat_data.get("meter_assumption"),
            },
            "artifacts": {
                "beats_file": str(beats_file),
                "beats_file_name": beats_file.name,
            },
        },
    )

    return {
        "song_path": str(song_path),
        "meta_path": str(song_meta_dir),
        "meta_file": str(meta_file),
        "beats_file": str(beats_file),
        "stems_dir": str(stems_dir),
        "beat_tracking_method": beat_data.get("method"),
    }


def main() -> int:
    result = analyze_song()
    print("Analyze complete:", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
