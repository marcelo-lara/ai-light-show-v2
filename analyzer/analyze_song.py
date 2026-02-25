from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

from src.beat_finder import find_beats_and_downbeats
from src.essentia_analysis import analyze_with_essentia
from src.essentia_analysis.common import is_stem_worth_analyzing
from src.split_stems import MODEL_NAME, TEMP_FILES_FOLDER, split_stems

META_PATH = "/app/meta"

SONGS_DIR = "/app/songs"


def warn(message: str) -> None:
    print(f"WARNING: {message}")


def _round_floats(value):
    if isinstance(value, float):
        return round(value, 3)
    if isinstance(value, dict):
        return {k: _round_floats(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_round_floats(v) for v in value]
    if isinstance(value, tuple):
        return [_round_floats(v) for v in value]
    return value


def _dump_json(path: Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_round_floats(payload), f, indent=2)


def _merge_json_file(path: Path, updates: dict) -> None:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}
    _deep_update(data, updates)
    _dump_json(path, data)


def _deep_update(base: dict, updates: dict) -> None:
    for key, value in updates.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_update(base[key], value)
        else:
            base[key] = value


def list_songs(songs_dir: str | Path = SONGS_DIR) -> List[Path]:
    p = Path(songs_dir)
    if not p.exists():
        return []
    exts = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"}
    files = [f for f in sorted(p.iterdir()) if f.suffix.lower() in exts and f.is_file()]
    return files


def choose_song_dialog(songs: List[Path]) -> Optional[Path]:
    if not songs:
        warn(f"No songs found in {SONGS_DIR}")
        return None
    for i, s in enumerate(songs, start=1):
        print(f"{i}. {s.name}")
    print("0. Cancel")
    try:
        choice = int(input("Choose a song number: ").strip())
    except Exception:
        warn("Invalid selection")
        return None
    if choice == 0:
        return None
    if 1 <= choice <= len(songs):
        return songs[choice - 1]
    warn("Selection out of range")
    return None


def autodetect_device() -> str:
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception as exc:
        warn(f"Could not detect CUDA availability ({exc}); using cpu")
        return "cpu"


def resolve_song(song_arg: str | None, songs_dir: str | Path = SONGS_DIR) -> Optional[Path]:
    songs = list_songs(songs_dir)
    if song_arg:
        selected = Path(songs_dir) / song_arg
        return selected
    if songs:
        warn(f"No --song provided; using first available song: {songs[0].name}")
        return songs[0]
    warn("No songs available to analyze")
    return None


def run_split_stems_for(song_path: Path, device: str) -> Optional[Path]:
    print(f"Starting split stems for {song_path.name} on device={device}")
    try:
        stems_dir, stem_files = split_stems(
            song_path=song_path,
            output_dir=TEMP_FILES_FOLDER,
            model=MODEL_NAME,
            device=device,
            meta_dir=_song_meta_dir(song_path, META_PATH),
        )
        _merge_json_file(
            CENTRAL_META_FILE,
            {
                song_path.stem: {
                    "model": MODEL_NAME,
                    "device": device,
                    "stems_dir": str(stems_dir),
                    "stems": stem_files,
                }
            },
        )
        print("Split stems complete. Output:", stems_dir)
        return Path(stems_dir)
    except Exception as e:
        warn(f"split_stems failed: {e}")
        return None


def run_beat_finder_for(song_path: Path, meta_path: str | Path = META_PATH) -> Optional[dict]:
    print(f"Running beat finder for {song_path.name}")
    try:
        beat_data = find_beats_and_downbeats(song_path=song_path)

        meta_root = Path(meta_path).expanduser().resolve()
        song_meta_dir = _song_meta_dir(song_path, meta_root)
        song_meta_dir.mkdir(parents=True, exist_ok=True)

        beats_file = song_meta_dir / "beats.json"
        _dump_json(
            beats_file,
            {
                "beats": beat_data.get("beats", []),
                "downbeats": beat_data.get("downbeats", []),
            },
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
                    "beats_file": str(beats_file)
                },
            },
        )
        print("Beat finding complete. Beats file:", beats_file)
        return beat_data
    except Exception as e:
        warn(f"Beat finder failed: {e}")
        return None


def run_essentia_analysis_for(song_path: Path, meta_path: str | Path = META_PATH) -> Optional[dict]:
    print(f"Running Essentia analysis for {song_path.name}")
    try:
        if not song_path.exists() or not song_path.is_file():
            warn(f"Song file does not exist: {song_path}")
            return None

        device = autodetect_device()
        if device != "cuda":
            warn("CUDA is not available; Essentia analysis will run on cpu")

        meta_root = Path(meta_path).expanduser().resolve()
        song_meta_dir = _song_meta_dir(song_path, meta_root)
        essentia_dir = song_meta_dir / "essentia"
        essentia_dir.mkdir(parents=True, exist_ok=True)

        part_name = "mix"
        print(f"Analyzing entire song as part: {part_name}")
        artifacts = analyze_with_essentia(str(song_path), str(essentia_dir), part_name)
        rhythm = artifacts.get("rhythm", {}).get("rhythm", {}) if isinstance(artifacts, dict) else {}
        bpm_value = rhythm.get("bpm")
        try:
            if bpm_value is not None and float(bpm_value) == 0.0:
                warn("Essentia returned bpm=0.0; check audio quality or analysis parameters")
        except (TypeError, ValueError):
            warn(f"Essentia returned non-numeric bpm value: {bpm_value}")

        # Load metadata to get stems
        if CENTRAL_META_FILE.exists():
            with open(CENTRAL_META_FILE, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            song_data = metadata.get(song_path.stem, {})
            stems_dir = song_data.get("stems_dir")
            stems = song_data.get("stems", [])
            if stems_dir and stems:
                stems_path = Path(stems_dir)
                for stem_name in ["bass", "drums", "vocals", "other"]:
                    stem_file = stems_path / f"{stem_name}.wav"
                    if stem_file.exists() and is_stem_worth_analyzing(str(stem_file)):
                        print(f"Analyzing stem: {stem_name}")
                        stem_artifacts = analyze_with_essentia(str(stem_file), str(essentia_dir), stem_name)
                        # Merge stem artifacts into main artifacts
                        for key, value in stem_artifacts.items():
                            artifacts[f"{stem_name}_{key}"] = value
                    else:
                        print(f"Skipping stem: {stem_name} (not worth analyzing)")

        essentia_artifacts = {}
        for artifact_name in artifacts:
            json_path = essentia_dir / f"{artifact_name}.json"
            svg_path = essentia_dir / f"{artifact_name}.svg"
            essentia_artifacts[artifact_name] = {
                "json": str(json_path),
                "svg": str(svg_path),
            }

        # Update info.json
        _merge_json_file(CENTRAL_META_FILE, {song_path.stem: {"artifacts": {"essentia": essentia_artifacts}}})

        print("Essentia analysis complete.")
        return artifacts
    except Exception as e:
        warn(f"Essentia analysis failed: {e}")
        return None


def _song_name(song_path: str | Path) -> str:
    return Path(song_path).expanduser().resolve().stem


def _song_meta_dir(song_path: str | Path, meta_path: str | Path) -> Path:
    return Path(meta_path).expanduser().resolve() / _song_name(song_path)


def _meta_file_path(song_path: str | Path, meta_path: str | Path) -> Path:
    return _song_meta_dir(song_path, meta_path) / f"info.json"


def _merge_json_file(path: Path, updates: dict) -> None:
    payload: dict = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    payload.update(updates)
    _dump_json(path, payload)


def analyze_song(
    song_path: str | Path,
    meta_path: str | Path = META_PATH,
    stems_output_dir: str | Path = TEMP_FILES_FOLDER,
    device: Optional[str] = None,
) -> dict:
    """Run the analyzer pipeline for one song.

    Current pipeline:
    1) Split stems with Demucs.
    2) Find beats/downbeats and write beat artifacts.
    """
    song_path = Path(song_path).expanduser().resolve()
    if device is None:
        device = autodetect_device()
    meta_root = Path(meta_path).expanduser().resolve()
    song_meta_dir = _song_meta_dir(song_path, meta_root)
    song_meta_dir.mkdir(parents=True, exist_ok=True)

    stems_dir, stem_files = split_stems(
        song_path=song_path,
        output_dir=stems_output_dir,
        model=MODEL_NAME,
        device=device,
        meta_dir=song_meta_dir,
    )

    _merge_json_file(
        CENTRAL_META_FILE,
        {
            song_path.stem: {
                "model": MODEL_NAME,
                "device": device,
                "stems_dir": str(stems_dir),
                "stems": stem_files,
            }
        },
    )

    # 2. Find beats and downbeats (librosa only)
    beat_data = find_beats_and_downbeats(song_path=song_path)

    beats_file = song_meta_dir / "beats.json"
    _dump_json(
        beats_file,
        {
            "beats": beat_data.get("beats", []),
            "downbeats": beat_data.get("downbeats", []),
        },
    )

    meta_file = CENTRAL_META_FILE
    _merge_json_file(
        meta_file,
        {
            song_path.stem: {
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
            }
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Light Show Analyzer")
    parser.add_argument('--song', type=str, default=None, help='Song file name in songs dir')
    parser.add_argument('--split-stems', action='store_true', help='Run stem splitting')
    parser.add_argument('--beat-finder', action='store_true', help='Run beat finder')
    parser.add_argument('--essentia-analysis', action='store_true', help='Run Essentia analysis')
    args = parser.parse_args()

    current_song = resolve_song(args.song)
    if current_song is None:
        return 1

    device = autodetect_device()

    # If CLI actions specified, run them and exit
    if args.split_stems or args.beat_finder or args.essentia_analysis:
        if not current_song.exists():
            warn(f"Song file does not exist: {current_song}")
            return 1
        if args.split_stems:
            run_split_stems_for(current_song, device)
        if args.beat_finder:
            run_beat_finder_for(current_song)
        if args.essentia_analysis:
            run_essentia_analysis_for(current_song)
        return 0

    # Interactive mode
    while True:
        print("\nSong:", current_song.name)
        print("0. Change Song")
        print("1. Split Stems")
        print("2. Beat Finder")
        print("3. Essentia Analysis")
        print("4. Exit")
        choice = input("Choose an option: ").strip()
        if choice == "0":
            songs = list_songs()
            selection = choose_song_dialog(songs)
            if selection:
                current_song = selection
        elif choice == "1":
            if not current_song.exists():
                warn(f"Current song file does not exist: {current_song}")
                continue
            run_split_stems_for(current_song, device)
        elif choice == "2":
            if not current_song.exists():
                warn(f"Current song file does not exist: {current_song}")
                continue
            run_beat_finder_for(current_song)
        elif choice == "3":
            if not current_song.exists():
                warn(f"Current song file does not exist: {current_song}")
                continue
            run_essentia_analysis_for(current_song)
        elif choice == "4":
            print("Exiting.")
            break
        else:
            warn("Invalid choice")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
