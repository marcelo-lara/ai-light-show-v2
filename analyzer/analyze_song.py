from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, List, Optional

from src.playlists import execute_full_artifact_playlist
from src.report_tool.beat_comparison import run_compare_beat_times_for
from src.tasks import init_song as init_song_task
from src.tasks.common import autodetect_device, warn
from src.tasks.essentia_analysis import run as run_essentia_analysis_task
from src.tasks.find_beats import run as run_find_beats_task
from src.tasks.find_chord_patterns import run as run_find_chord_patterns_task
from src.tasks.find_chords import run as run_find_chords_task
from src.tasks.find_sections import run as run_find_sections_task
from src.tasks.find_song_features import run as run_find_song_features_task
from src.tasks.find_stem_patterns import run as run_find_stem_patterns_task
from src.tasks.generate_md import run as run_generate_md_task
from src.tasks.import_moises_task import run as run_import_moises_task
from src.tasks.split_stems import run as run_split_stems_task
from src.tasks.stereo_analysis import run as run_stereo_analysis_task

META_PATH = os.environ.get("META_PATH", "/app/meta")
SONGS_DIR = os.environ.get("SONGS_DIR", "/app/songs")


def _is_escape_input(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized in {"\x1b", "esc", "escape"}


def list_songs(songs_dir: str | Path = SONGS_DIR) -> List[Path]:
    path = Path(songs_dir)
    if not path.exists():
        return []
    exts = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg"}
    return [file_path for file_path in sorted(path.iterdir()) if file_path.suffix.lower() in exts and file_path.is_file()]


def choose_song_dialog(songs: List[Path]) -> Optional[Path]:
    if not songs:
        warn(f"No songs found in {SONGS_DIR}")
        return None
    for index, song_path in enumerate(songs, start=1):
        print(f"{index}. {song_path.name}")
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


def resolve_song(song_arg: str | None, songs_dir: str | Path = SONGS_DIR) -> Optional[Path]:
    songs = list_songs(songs_dir)
    if song_arg:
        return Path(songs_dir) / song_arg
    if songs:
        warn(f"No --song provided; using first available song: {songs[0].name}")
        return songs[0]
    warn("No songs available to analyze")
    return None


def run_init_song_for(song_path: Path, meta_path: str | Path = META_PATH) -> dict[str, str]:
    return init_song_task.run({"song_path": str(song_path), "meta_path": str(meta_path)})


def run_split_stems_for(song_path: Path, device: str, meta_path: str | Path = META_PATH, progress_callback=None) -> Path | None:
    return run_split_stems_task({"song_path": str(song_path), "meta_path": str(meta_path), "device": device}, progress_callback=progress_callback)


def run_beat_finder_for(song_path: Path, meta_path: str | Path = META_PATH, progress_callback=None) -> dict[str, Any] | None:
    return run_find_beats_task({"song_path": str(song_path), "meta_path": str(meta_path)}, progress_callback=progress_callback)


def run_essentia_analysis_for(song_path: Path, meta_path: str | Path = META_PATH, progress_callback=None) -> dict[str, Any] | None:
    return run_essentia_analysis_task({"song_path": str(song_path), "meta_path": str(meta_path)}, progress_callback=progress_callback)


def run_import_moises_for(song_path: Path, meta_path: str | Path = META_PATH, progress_callback=None) -> dict[str, Any] | None:
    return run_import_moises_task({"song_path": str(song_path), "meta_path": str(meta_path)}, progress_callback=progress_callback)


def run_generate_md_for(song_path: Path, meta_path: str | Path = META_PATH, progress_callback=None) -> Path | None:
    return run_generate_md_task({"song_path": str(song_path), "meta_path": str(meta_path)}, progress_callback=progress_callback)


def run_find_chords_for(song_path: Path, meta_path: str | Path = META_PATH, output_name: str = "beats.json", progress_callback=None) -> dict[str, Any] | None:
    return run_find_chords_task({"song_path": str(song_path), "meta_path": str(meta_path), "output_name": output_name}, progress_callback=progress_callback)


def run_find_chord_patterns_for(song_path: Path, meta_path: str | Path = META_PATH, progress_callback=None) -> dict[str, Any]:
    return run_find_chord_patterns_task({"song_path": str(song_path), "meta_path": str(meta_path)}, progress_callback=progress_callback)


def run_find_stem_patterns_for(song_path: Path, meta_path: str | Path = META_PATH, progress_callback=None) -> dict[str, Any]:
    return run_find_stem_patterns_task({"song_path": str(song_path), "meta_path": str(meta_path)}, progress_callback=progress_callback)


def run_find_sections_for(song_path: Path, meta_path: str | Path = META_PATH, output_name: str = "sections.json", progress_callback=None) -> dict[str, Any] | None:
    return run_find_sections_task({"song_path": str(song_path), "meta_path": str(meta_path), "output_name": output_name}, progress_callback=progress_callback)


def run_find_song_features_for(song_path: Path, meta_path: str | Path = META_PATH, progress_callback=None) -> Path | None:
    return run_find_song_features_task({"song_path": str(song_path), "meta_path": str(meta_path)}, progress_callback=progress_callback)


def run_stereo_analysis_for(song_path: Path, meta_path: str | Path = META_PATH, progress_callback=None) -> dict[str, Any] | None:
    return run_stereo_analysis_task({"song_path": str(song_path), "meta_path": str(meta_path)}, progress_callback=progress_callback)


def run_full_artifact_playlist_for(song_path: Path, meta_path: str | Path = META_PATH, device: str | None = None, progress_callback=None) -> dict[str, Any]:
    return execute_full_artifact_playlist(song_path, meta_path, device=device, progress_callback=progress_callback)


def analyze_all_songs(songs_dir: str | Path = SONGS_DIR, meta_path: str | Path = META_PATH, device: Optional[str] = None) -> list[dict[str, Any]]:
    songs = list_songs(songs_dir)
    if not songs:
        warn(f"No songs available to analyze in {songs_dir}")
        return []
    resolved_device = device or autodetect_device()
    results: list[dict[str, Any]] = []
    for song_path in songs:
        print(f"\nAnalyzing song: {song_path.name}")
        if not song_path.exists():
            warn(f"Song file does not exist: {song_path}")
            results.append({"song": song_path.name, "steps": [], "status": "missing"})
            continue
        playlist = run_full_artifact_playlist_for(song_path, meta_path=meta_path, device=resolved_device)
        results.append({"song": song_path.name, "steps": [item["task_type"] for item in playlist["results"]], "status": playlist["status"]})
    print(f"Completed batch analysis for {len(results)} songs")
    return results


def analyze_song(song_path: str | Path, meta_path: str | Path = META_PATH, stems_output_dir: str | Path = "", device: Optional[str] = None) -> dict[str, Any]:
    del stems_output_dir
    song_file = Path(song_path).expanduser().resolve()
    playlist = run_full_artifact_playlist_for(song_file, meta_path=meta_path, device=device or autodetect_device())
    beats_file = Path(meta_path).expanduser().resolve() / song_file.stem / "beats.json"
    stems_dir = Path(meta_path).expanduser().resolve() / song_file.stem / "stems"
    return {"song": song_file.stem, "stems_dir": str(stems_dir), "beats_file": str(beats_file), "status": playlist["status"]}


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Light Show Analyzer")
    parser.add_argument("--song", type=str, default=None, help="Song file name in songs dir")
    parser.add_argument("--init-song", action="store_true", help="Initialize canonical song metadata")
    parser.add_argument("--split-stems", action="store_true", help="Run stem splitting")
    parser.add_argument("--beat-finder", action="store_true", help="Run beat finder")
    parser.add_argument("--essentia-analysis", action="store_true", help="Run Essentia analysis")
    parser.add_argument("--find-song-features", action="store_true", help="Generate song feature metadata")
    parser.add_argument("--stereo-analysis", action="store_true", help="Annotate notable stereo differences into features.json")
    parser.add_argument("--find-chords", action="store_true", help="Infer chord labels onto beats metadata")
    parser.add_argument("--find-chord-patterns", action="store_true", help="Group repeating chord progressions from canonical beat metadata")
    parser.add_argument("--find-stem-patterns", action="store_true", help="Group repeating stem loudness and envelope profiles using chord pattern windows")
    parser.add_argument("--find-sections", action="store_true", help="Infer song section labels")
    parser.add_argument("--import-moises", action="store_true", help="Import Moises chords")
    parser.add_argument("--generate-md", action="store_true", help="Generate markdown from sections metadata")
    parser.add_argument("--full-artifact-playlist", action="store_true", help="Run the full artifact playlist for the selected song")
    parser.add_argument("--beats-output-name", type=str, default="beats.json", help="Output file name for chord inference")
    parser.add_argument("--sections-output-name", type=str, default="sections.json", help="Output file name for section inference")
    args = parser.parse_args()

    current_song = resolve_song(args.song)
    if current_song is None:
        return 1
    device = autodetect_device()
    has_cli_action = any(
        [
            args.init_song,
            args.split_stems,
            args.beat_finder,
            args.essentia_analysis,
            args.find_song_features,
            args.stereo_analysis,
            args.find_chords,
            args.find_chord_patterns,
            args.find_stem_patterns,
            args.find_sections,
            args.import_moises,
            args.generate_md,
            args.full_artifact_playlist,
        ]
    )
    if has_cli_action:
        if not current_song.exists():
            warn(f"Song file does not exist: {current_song}")
            return 1
        if args.init_song:
            run_init_song_for(current_song)
        if args.split_stems:
            run_split_stems_for(current_song, device)
        if args.beat_finder:
            run_beat_finder_for(current_song)
        if args.essentia_analysis:
            run_essentia_analysis_for(current_song)
        if args.find_song_features:
            run_find_song_features_for(current_song)
        if args.stereo_analysis:
            run_stereo_analysis_for(current_song)
        if args.find_chords:
            run_find_chords_for(current_song, output_name=args.beats_output_name)
        if args.find_chord_patterns:
            run_find_chord_patterns_for(current_song)
        if args.find_stem_patterns:
            run_find_stem_patterns_for(current_song)
        if args.find_sections:
            run_find_sections_for(current_song, output_name=args.sections_output_name)
        if args.import_moises:
            run_import_moises_for(current_song)
        if args.generate_md:
            run_generate_md_for(current_song)
        if args.full_artifact_playlist:
            run_full_artifact_playlist_for(current_song, device=device)
        return 0

    while True:
        print("\nSong:", current_song.name)
        print("0. Change Song")
        print("1. Init Song")
        print("2. Split Stems")
        print("3. Beat Finder")
        print("4. Essentia Analysis")
        print("5. Find Song Features")
        print("6. Stereo Analysis")
        print("7. Find Chords")
        print("8. Find Chord Patterns")
        print("9. Find Stem Patterns")
        print("10. Find Sections")
        print("11. Compare Beat Times")
        print("12. Import Moises Chords")
        print("13. Generate MD file")
        print("14. Full Artifact Playlist")
        print("15. Analyze All Songs")
        print("16. Exit (Esc also exits)")
        choice = input("Choose an option: ").strip()
        if _is_escape_input(choice) or choice == "16":
            print("Exiting.")
            break
        if choice == "0":
            selection = choose_song_dialog(list_songs())
            if selection:
                current_song = selection
        elif choice == "1":
            run_init_song_for(current_song)
        elif choice == "2":
            run_split_stems_for(current_song, device)
        elif choice == "3":
            run_beat_finder_for(current_song)
        elif choice == "4":
            run_essentia_analysis_for(current_song)
        elif choice == "5":
            run_find_song_features_for(current_song)
        elif choice == "6":
            run_stereo_analysis_for(current_song)
        elif choice == "7":
            run_find_chords_for(current_song)
        elif choice == "8":
            run_find_chord_patterns_for(current_song)
        elif choice == "9":
            run_find_stem_patterns_for(current_song)
        elif choice == "10":
            run_find_sections_for(current_song)
        elif choice == "11":
            run_compare_beat_times_for(current_song)
        elif choice == "12":
            run_import_moises_for(current_song)
        elif choice == "13":
            run_generate_md_for(current_song)
        elif choice == "14":
            run_full_artifact_playlist_for(current_song, device=device)
        elif choice == "15":
            analyze_all_songs(device=device)
        else:
            warn("Invalid choice")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())