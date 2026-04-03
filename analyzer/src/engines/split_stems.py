"""Split a song into stems using Demucs."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from shutil import which

import soundfile as sf

SONG_PATH = "/app/songs/Yonaka - Seize the Power.mp3"
TEMP_FILES_FOLDER = "/app/analyzer/temp_files/"
MODEL_NAME = "htdemucs"


def _demucs_base_command() -> list[str]:
    if which("demucs") is not None:
        return ["demucs"]
    return [sys.executable, "-m", "demucs.separate"]


def _save_with_soundfile(path: str, wav, sample_rate: int, encoding=None, bits_per_sample=None):
    subtype_map = {("PCM_S", 16): "PCM_16", ("PCM_S", 24): "PCM_24", ("PCM_S", 32): "PCM_32", ("PCM_F", 32): "FLOAT"}
    data = wav.detach().cpu().transpose(0, 1).numpy()
    sf.write(path, data, sample_rate, subtype=subtype_map.get((encoding, bits_per_sample)))


def _run_demucs(command: list[str]) -> None:
    from demucs import audio as demucs_audio
    from demucs import separate as demucs_separate

    original_save = demucs_audio.ta.save
    demucs_audio.ta.save = _save_with_soundfile
    try:
        demucs_separate.main(command[1:])
    finally:
        demucs_audio.ta.save = original_save


def split_stems(
    song_path: str | Path,
    output_dir: str | Path,
    model: str = MODEL_NAME,
    device: str = "cuda",
    mp3: bool = False,
    jobs: int = 0,
    meta_dir: str | Path | None = None,
) -> tuple[Path, list[str]]:
    song_path = Path(song_path).expanduser().resolve()
    output_dir = Path(output_dir).expanduser().resolve()
    if not song_path.exists():
        raise FileNotFoundError(f"Song file not found: {song_path}")
    if not song_path.is_file():
        raise ValueError(f"Song path is not a file: {song_path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    command = _demucs_base_command() + ["--name", model, "--device", device, "--jobs", str(jobs), "--out", str(output_dir), str(song_path)]
    if mp3:
        command.insert(-1, "--mp3")
    print("Running:", " ".join(command))
    _run_demucs(command)
    stems_dir = output_dir / model / song_path.stem
    if not stems_dir.exists():
        raise RuntimeError(f"Demucs finished but expected stems directory was not found: {stems_dir}")
    stem_files = sorted([str(path.resolve()) for path in stems_dir.glob("*") if path.is_file()])
    if meta_dir is not None:
        Path(meta_dir).expanduser().resolve().mkdir(parents=True, exist_ok=True)
    return stems_dir, stem_files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Split audio into stems (vocals, drums, bass, etc.) with Demucs.")
    parser.add_argument("--song", default=SONG_PATH, help="Path to input song file.")
    parser.add_argument("--out", default=TEMP_FILES_FOLDER, help="Directory where Demucs output should be written.")
    parser.add_argument("--model", default=MODEL_NAME, help="Demucs model name (default: htdemucs).")
    parser.add_argument("--device", default="cuda", choices=["cpu", "cuda", "mps"], help="Compute device used by Demucs.")
    parser.add_argument("--meta-dir", default=None, help="Optional meta output directory.")
    parser.add_argument("--mp3", action="store_true", help="Export mp3 stems instead of wav stems.")
    parser.add_argument("--jobs", type=int, default=0, help="Number of workers used by Demucs (0 = auto).")
    return parser.parse_args()


def main() -> int:
    args = parse_args() if len(sys.argv) > 1 else argparse.Namespace(song=SONG_PATH, out=TEMP_FILES_FOLDER, model=MODEL_NAME, device="cuda", meta_dir=None, mp3=False, jobs=0)
    try:
        stems_dir, _ = split_stems(song_path=args.song, output_dir=args.out, model=args.model, device=args.device, mp3=args.mp3, jobs=args.jobs, meta_dir=args.meta_dir)
    except (FileNotFoundError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Stems created in: {stems_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())