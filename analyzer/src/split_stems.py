"""Split a song into stems using Demucs.

This script can be run directly:
    python analyzer/src/split_strems.py

Or with custom args:
    python analyzer/src/split_strems.py --song /path/to/song.mp3 --device cuda
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from shutil import which

# Config
SONG_PATH = "/app/songs/Yonaka - Seize the Power.mp3"
TEMP_FILES_FOLDER = "/app/analyzer/temp_files/"
MODEL_NAME = "htdemucs"


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


def _demucs_base_command() -> list[str]:
    """Return the best available command for Demucs."""
    if which("demucs") is not None:
        return ["demucs"]
    return [sys.executable, "-m", "demucs.separate"]


def _merge_json_file(path: Path, updates: dict) -> None:
    payload: dict = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    payload.update(updates)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_round_floats(payload), f, indent=2)


def split_stems(
    song_path: str | Path,
    output_dir: str | Path,
    model: str = MODEL_NAME,
    device: str = "cuda",
    mp3: bool = False,
    jobs: int = 0,
    meta_dir: str | Path | None = None,
) -> Path:
    """Run Demucs and return the directory containing generated stems."""
    song_path = Path(song_path).expanduser().resolve()
    output_dir = Path(output_dir).expanduser().resolve()

    if not song_path.exists():
        raise FileNotFoundError(f"Song file not found: {song_path}")
    if not song_path.is_file():
        raise ValueError(f"Song path is not a file: {song_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    command = _demucs_base_command() + [
        "--name",
        model,
        "--device",
        device,
        "--jobs",
        str(jobs),
        "--out",
        str(output_dir),
        str(song_path),
    ]
    if mp3:
        command.insert(-1, "--mp3")

    print("Running:", " ".join(command))
    subprocess.run(command, check=True)

    # Demucs output path format: <out>/<model>/<song_stem_name>/
    stems_dir = output_dir / model / song_path.stem
    if not stems_dir.exists():
        raise RuntimeError(
            "Demucs finished but expected stems directory was not found: "
            f"{stems_dir}"
        )

    if meta_dir is not None:
        meta_dir = Path(meta_dir).expanduser().resolve()
        meta_dir.mkdir(parents=True, exist_ok=True)
        stem_files = sorted(
            [str(p.resolve()) for p in stems_dir.glob("*") if p.is_file()]
        )

    return stems_dir, stem_files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split audio into stems (vocals, drums, bass, etc.) with Demucs."
    )
    parser.add_argument("--song", default=SONG_PATH, help="Path to input song file.")
    parser.add_argument(
        "--out",
        default=TEMP_FILES_FOLDER,
        help="Directory where Demucs output should be written.",
    )
    parser.add_argument(
        "--model",
        default=MODEL_NAME,
        help="Demucs model name (default: htdemucs).",
    )
    parser.add_argument(
        "--device",
        default="cuda",
        choices=["cpu", "cuda", "mps"],
        help="Compute device used by Demucs.",
    )
    parser.add_argument(
        "--meta-dir",
        default=None,
        help="Optional meta output directory. Writes {song_name}.json when set.",
    )
    parser.add_argument(
        "--mp3",
        action="store_true",
        help="Export mp3 stems instead of wav stems.",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=0,
        help="Number of workers used by Demucs (0 = auto).",
    )
    return parser.parse_args()


def main() -> int:
    if len(sys.argv) == 1:
        print(f"Running test split with provided song: {SONG_PATH}")
        try:
            stems_dir = split_stems(
                song_path=SONG_PATH,
                output_dir=TEMP_FILES_FOLDER,
                model=MODEL_NAME,
                device="cuda",
            )
        except (
            FileNotFoundError,
            ValueError,
            RuntimeError,
            subprocess.CalledProcessError,
        ) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

        print(f"Test stems created in: {stems_dir}")
        return 0

    args = parse_args()
    try:
        stems_dir = split_stems(
            song_path=args.song,
            output_dir=args.out,
            model=args.model,
            device=args.device,
            mp3=args.mp3,
            jobs=args.jobs,
            meta_dir=args.meta_dir,
        )
    except (FileNotFoundError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Stems created in: {stems_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
