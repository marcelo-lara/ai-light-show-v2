from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, List, Optional

import librosa

from beat_comparison import run_compare_beat_times_for
from src.beat_finder import find_beats_and_downbeats
from src.essentia_analysis import analyze_with_essentia, build_loudness_hints
from src.essentia_analysis.common import is_stem_worth_analyzing
from src.moises import import_moises
from src.split_stems import MODEL_NAME, TEMP_FILES_FOLDER, split_stems

META_PATH = os.environ.get("META_PATH", "/app/meta")
SONGS_DIR = os.environ.get("SONGS_DIR", "/app/songs")
ESSENTIA_FEATURES = ("rhythm", "loudness_envelope", "chroma_hpcp", "mel_bands", "spectral_centroid")


def warn(message: str) -> None:
    print(f"WARNING: {message}")


def _is_escape_input(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized in {"\x1b", "esc", "escape"}


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


def _dump_json(path: Path, payload: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_round_floats(payload), f, indent=2)


def _deep_update(base: dict, updates: dict) -> None:
    for key, value in updates.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_update(base[key], value)
        else:
            base[key] = value


def _merge_json_file(path: Path, updates: dict) -> None:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}
    _deep_update(data, updates)
    _dump_json(path, data)


def _load_json_file(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _song_name(song_path: str | Path) -> str:
    return Path(song_path).expanduser().resolve().stem


def _song_meta_dir(song_path: str | Path, meta_path: str | Path) -> Path:
    return Path(meta_path).expanduser().resolve() / _song_name(song_path)


def _meta_file_path(song_path: str | Path, meta_path: str | Path) -> Path:
    return _song_meta_dir(song_path, meta_path) / "info.json"


def _moises_dir(song_path: str | Path, meta_path: str | Path) -> Path:
    return _song_meta_dir(song_path, meta_path) / "moises"


def _read_sample_rate(audio_path: str | Path) -> int | None:
    try:
        return int(librosa.get_samplerate(str(audio_path)))
    except Exception as exc:
        warn(f"Could not read sample rate for {audio_path}: {exc}")
        return None


def _load_list_file(path: Path) -> list[Any]:
    if not path.exists():
        return []
    payload = _load_json_file(path)
    return payload if isinstance(payload, list) else []


def _load_sections(song_meta_dir: Path) -> list[dict[str, Any]]:
    sections = _load_list_file(song_meta_dir / "sections.json")
    normalized: list[dict[str, Any]] = []
    for index, section in enumerate(sections, start=1):
        if not isinstance(section, dict):
            continue
        start_value = float(section.get("start_s", section.get("start", 0.0)) or 0.0)
        end_value = float(section.get("end_s", section.get("end", start_value)) or start_value)
        normalized.append({"name": str(section.get("name") or section.get("label") or f"Section {index}"), "start_s": round(start_value, 3), "end_s": round(max(end_value, start_value), 3)})
    return normalized


def _has_moises_mix_data(song_path: str | Path, meta_path: str | Path) -> bool:
    moises_dir = _moises_dir(song_path, meta_path)
    return bool(_load_list_file(moises_dir / "beats.json") or _load_list_file(moises_dir / "chords.json"))


def _normalize_analyzer_beats(beat_data: dict) -> list[dict]:
    beats = [float(time) for time in beat_data.get("beats", [])]
    downbeats = [float(time) for time in beat_data.get("downbeats", [])]
    if not beats:
        return []
    first_downbeat_index = 0
    if downbeats:
        first_downbeat = downbeats[0]
        first_downbeat_index = min(range(len(beats)), key=lambda index: abs(beats[index] - first_downbeat))

    normalized = []
    for index, time_value in enumerate(beats):
        offset = index - first_downbeat_index
        normalized.append(
            {
                "time": round(time_value, 3),
                "beat": (offset % 4) + 1,
                "bar": (offset // 4) + 1,
                "bass": None,
                "chord": None,
            }
        )
    return normalized


def _annotate_beat_types(beats: list[dict]) -> list[dict]:
    annotated: list[dict] = []
    for beat_event in beats:
        annotated.append({**beat_event, "type": "downbeat" if beat_event.get("beat") == 1 else "beat"})
    return annotated


def _beat_tracking_payload(method: str, beats: list[dict], beat_data: Optional[dict] = None) -> dict:
    beat_data = beat_data or {}
    return {
        "method": method,
        "tempo_bpm": beat_data.get("tempo_bpm"),
        "sample_rate": beat_data.get("sample_rate"),
        "beat_count": len(beats),
        "downbeat_count": sum(1 for beat in beats if beat.get("beat") == 1),
        "beat_strength_mean": beat_data.get("beat_strength_mean"),
        "downbeat_strength_mean": beat_data.get("downbeat_strength_mean"),
        "meter_assumption": beat_data.get("meter_assumption", "4/4"),
    }


def _write_song_beats(song_path: Path, meta_root: Path, beats: list[dict], source: str, beat_data: Optional[dict] = None) -> Path:
    beats_file = _song_meta_dir(song_path, meta_root) / "beats.json"
    annotated_beats = _annotate_beat_types(beats)
    _dump_json(beats_file, annotated_beats)
    artifacts = {"beats_file": str(beats_file)}
    moises_chords_file = _moises_dir(song_path, meta_root) / "chords.json"
    if source == "moises" and moises_chords_file.exists():
        artifacts["chords_file"] = str(moises_chords_file)
    _merge_json_file(
        _meta_file_path(song_path, meta_root),
        {
            "song_name": song_path.stem,
            "song_path": str(song_path),
            "beats_source": source,
            "beat_tracking": _beat_tracking_payload(source, annotated_beats, beat_data),
            "artifacts": artifacts,
        },
    )
    return beats_file


def _artifact_file_stems_for_part(part_name: str) -> dict[str, str]:
    if part_name == "mix":
        return {feature: feature for feature in ESSENTIA_FEATURES}
    return {feature: f"{part_name}_{feature}" for feature in ESSENTIA_FEATURES}


def _build_essentia_manifest(essentia_dir: Path, part_artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    manifest: dict[str, Any] = {}
    for part_name, artifacts in part_artifacts.items():
        file_stems = _artifact_file_stems_for_part(part_name)
        manifest[part_name] = {}
        for artifact_name in artifacts:
            file_stem = file_stems.get(artifact_name, artifact_name)
            manifest[part_name][artifact_name] = {
                "json": str(essentia_dir / f"{file_stem}.json"),
                "svg": str(essentia_dir / f"{file_stem}.svg"),
            }
    return manifest


def analyze_all_songs(
    songs_dir: str | Path = SONGS_DIR,
    meta_path: str | Path = META_PATH,
    device: Optional[str] = None,
) -> list[dict[str, Any]]:
    songs = list_songs(songs_dir)
    if not songs:
        warn(f"No songs available to analyze in {songs_dir}")
        return []

    if device is None:
        device = autodetect_device()

    results: list[dict[str, Any]] = []
    for song_path in songs:
        print(f"\nAnalyzing song: {song_path.name}")
        song_result: dict[str, Any] = {"song": song_path.name, "steps": []}
        if not song_path.exists():
            warn(f"Song file does not exist: {song_path}")
            song_result["status"] = "missing"
            results.append(song_result)
            continue

        run_split_stems_for(song_path, device, meta_path=meta_path)
        song_result["steps"].append("split_stems")

        if _has_moises_mix_data(song_path, meta_path):
            print(f"Deferring beat import to Moises mix data for {song_path.name}")
        else:
            run_beat_finder_for(song_path, meta_path=meta_path)
            song_result["steps"].append("beat_finder")

        run_essentia_analysis_for(song_path, meta_path=meta_path)
        song_result["steps"].append("essentia_analysis")

        if _has_moises_mix_data(song_path, meta_path):
            run_import_moises_for(song_path, meta_path=meta_path)
            song_result["steps"].append("import_moises")

        song_result["status"] = "completed"
        results.append(song_result)

    print(f"Completed batch analysis for {len(results)} songs")
    return results


def list_songs(songs_dir: str | Path = SONGS_DIR) -> List[Path]:
    p = Path(songs_dir)
    if not p.exists():
        return []
    exts = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"}
    return [f for f in sorted(p.iterdir()) if f.suffix.lower() in exts and f.is_file()]


def choose_song_dialog(songs: List[Path]) -> Optional[Path]:
    if not songs:
        warn(f"No songs found in {SONGS_DIR}")
        return None
    for i, s in enumerate(songs, start=1):
        print(f"{i}. {s.name}")
    print("0. Cancel (Esc also cancels)")
    try:
        raw_choice = input("Choose a song number: ").strip()
        if _is_escape_input(raw_choice):
            return None
        choice = int(raw_choice)
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
        return Path(songs_dir) / song_arg
    if songs:
        warn(f"No --song provided; using first available song: {songs[0].name}")
        return songs[0]
    warn("No songs available to analyze")
    return None


def run_split_stems_for(song_path: Path, device: str, meta_path: str | Path = META_PATH) -> Optional[Path]:
    print(f"Starting split stems for {song_path.name} on device={device}")
    try:
        meta_root = Path(meta_path).expanduser().resolve()
        song_meta_dir = _song_meta_dir(song_path, meta_root)
        song_meta_dir.mkdir(parents=True, exist_ok=True)

        stems_dir, stem_files = split_stems(
            song_path=song_path,
            output_dir=TEMP_FILES_FOLDER,
            model=MODEL_NAME,
            device=device,
            meta_dir=song_meta_dir,
        )
        _merge_json_file(
            _meta_file_path(song_path, meta_root),
            {
                "song_name": song_path.stem,
                "song_path": str(song_path),
                "model": MODEL_NAME,
                "device": device,
                "stems_dir": str(stems_dir),
                "stems": stem_files,
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
        meta_root = Path(meta_path).expanduser().resolve()
        song_meta_dir = _song_meta_dir(song_path, meta_root)
        song_meta_dir.mkdir(parents=True, exist_ok=True)
        if _has_moises_mix_data(song_path, meta_root):
            print(f"Using Moises mix data for beats and chords: {song_path.name}")
            moises_beats = import_moises(song_path.stem, meta_path=meta_root)
            if moises_beats:
                beats_file = _write_song_beats(song_path, meta_root, moises_beats, "moises")
                print("Beat import complete. Beats file:", beats_file)
                return {"method": "moises", "beat_count": len(moises_beats)}
            warn("Moises mix data was present but unusable; falling back to analyzer beat finder")

        beat_data = find_beats_and_downbeats(song_path=song_path)
        normalized_beats = _normalize_analyzer_beats(beat_data)
        beats_file = _write_song_beats(song_path, meta_root, normalized_beats, "analyzer", beat_data)
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
        song_meta_dir.mkdir(parents=True, exist_ok=True)
        essentia_dir = song_meta_dir / "essentia"
        essentia_dir.mkdir(parents=True, exist_ok=True)

        part_name = "mix"
        mix_sample_rate = _read_sample_rate(song_path)
        print(f"Analyzing entire song as part: {part_name}")
        part_artifacts = {
            part_name: analyze_with_essentia(
                str(song_path),
                str(essentia_dir),
                part_name,
                sample_rate=mix_sample_rate,
                artifact_file_stems=_artifact_file_stems_for_part(part_name),
            )
        }
        rhythm = part_artifacts[part_name].get("rhythm", {}).get("rhythm", {}) if isinstance(part_artifacts[part_name], dict) else {}
        bpm_value = rhythm.get("bpm")
        try:
            if bpm_value is not None and float(bpm_value) == 0.0:
                warn("Essentia returned bpm=0.0; check audio quality or analysis parameters")
        except (TypeError, ValueError):
            warn(f"Essentia returned non-numeric bpm value: {bpm_value}")

        meta_file = _meta_file_path(song_path, meta_root)
        if meta_file.exists():
            metadata = _load_json_file(meta_file)
            stems_dir = metadata.get("stems_dir")
            stems = metadata.get("stems", [])
            if stems_dir and stems:
                stems_path = Path(stems_dir)
                for stem_name in ["bass", "drums", "vocals", "other"]:
                    stem_file = stems_path / f"{stem_name}.wav"
                    if stem_file.exists() and is_stem_worth_analyzing(str(stem_file)):
                        stem_sample_rate = _read_sample_rate(stem_file)
                        print(f"Analyzing stem: {stem_name}")
                        stem_artifacts = analyze_with_essentia(
                            str(stem_file),
                            str(essentia_dir),
                            stem_name,
                            sample_rate=stem_sample_rate,
                            artifact_file_stems=_artifact_file_stems_for_part(stem_name),
                        )
                        part_artifacts[stem_name] = stem_artifacts
                    else:
                        print(f"Skipping stem: {stem_name} (not worth analyzing)")

        hints_path = song_meta_dir / "hints.json"
        _dump_json(hints_path, build_loudness_hints(part_artifacts, _load_sections(song_meta_dir)))
        _merge_json_file(
            meta_file,
            {"artifacts": {"essentia": _build_essentia_manifest(essentia_dir, part_artifacts), "hints_file": str(hints_path)}},
        )

        print("Essentia analysis complete.")
        return part_artifacts
    except Exception as e:
        warn(f"Essentia analysis failed: {e}")
        return None


def run_import_moises_for(song_path: Path, meta_path: str | Path = META_PATH) -> None:
    print(f"Running import moises for {song_path.name}")
    try:
        meta_root = Path(meta_path).expanduser().resolve()
        moises_beats = import_moises(song_path.stem, meta_path=meta_root)
        if not moises_beats:
            warn(f"No usable Moises mix data found for {song_path.name}")
            return
        beats_file = _write_song_beats(song_path, meta_root, moises_beats, "moises")
        print("Moises import complete. Beats file:", beats_file)
    except Exception as e:
        warn(f"Import moises failed: {e}")


def analyze_song(
    song_path: str | Path,
    meta_path: str | Path = META_PATH,
    stems_output_dir: str | Path = TEMP_FILES_FOLDER,
    device: Optional[str] = None,
) -> dict:
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

    meta_file = _meta_file_path(song_path, meta_root)
    _merge_json_file(
        meta_file,
        {
            "song_name": song_path.stem,
            "song_path": str(song_path),
            "model": MODEL_NAME,
            "device": device,
            "stems_dir": str(stems_dir),
            "stems": stem_files,
        },
    )

    run_beat_finder_for(song_path, meta_root)
    beats_file = song_meta_dir / "beats.json"

    return {
        "song": song_path.stem,
        "stems_dir": str(stems_dir),
        "beats_file": str(beats_file),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Light Show Analyzer")
    parser.add_argument("--song", type=str, default=None, help="Song file name in songs dir")
    parser.add_argument("--split-stems", action="store_true", help="Run stem splitting")
    parser.add_argument("--beat-finder", action="store_true", help="Run beat finder")
    parser.add_argument("--essentia-analysis", action="store_true", help="Run Essentia analysis")
    parser.add_argument("--import-moises", action="store_true", help="Import Moises chords")
    args = parser.parse_args()

    if not any([args.split_stems, args.beat_finder, args.essentia_analysis, args.import_moises]):
        current_song = resolve_song(args.song)
    else:
        current_song = resolve_song(args.song)

    if current_song is None:
        return 1

    device = autodetect_device()

    if args.split_stems or args.beat_finder or args.essentia_analysis or args.import_moises:
        if not current_song.exists():
            warn(f"Song file does not exist: {current_song}")
            return 1
        if args.split_stems:
            run_split_stems_for(current_song, device)
        if args.beat_finder:
            run_beat_finder_for(current_song)
        if args.essentia_analysis:
            run_essentia_analysis_for(current_song)
        if args.import_moises:
            run_import_moises_for(current_song)
        return 0

    while True:
        print("\nSong:", current_song.name)
        print("0. Change Song")
        print("1. Split Stems")
        print("2. Beat Finder")
        print("3. Essentia Analysis")
        print("4. Compare Beat Times")
        print("5. Import Moises Chords")
        print("8. Analyze All Songs")
        print("9. Exit (Esc also exits)")
        choice = input("Choose an option: ").strip()
        if _is_escape_input(choice) or choice == "9":
            print("Exiting.")
            break
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
            if not current_song.exists():
                warn(f"Current song file does not exist: {current_song}")
                continue
            run_compare_beat_times_for(current_song)
        elif choice == "5":
            run_import_moises_for(current_song)
        elif choice == "8":
            analyze_all_songs(device=device)
        else:
            warn("Invalid choice")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
