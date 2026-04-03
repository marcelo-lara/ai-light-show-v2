from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from ..runtime.progress import ProgressCallback
from src.storage.song_meta import initialize_song_info, load_json_file, song_meta_dir

META_PATH = os.environ.get("META_PATH", "/app/meta")


def init_song(song_path: str | Path, meta_path: str | Path) -> Path:
    return initialize_song_info(song_path, meta_path)


def init_song_payload(song_path: str | Path, meta_path: str | Path) -> dict[str, str]:
    song_file = Path(song_path).expanduser().resolve()
    info_file = init_song(song_file, meta_path)
    meta_dir = song_meta_dir(song_file, meta_path)
    payload = load_json_file(info_file)
    return {
        "song": song_file.name,
        "song_dir": str(meta_dir),
        "info_file": str(info_file),
        "song_name": str(payload.get("song_name") or song_file.stem),
        "song_path": str(payload.get("song_path") or song_file),
    }


def run(params: dict[str, Any], progress_callback: ProgressCallback | None = None) -> dict[str, str]:
    del progress_callback
    return init_song_payload(params["song_path"], params.get("meta_path", "/app/meta"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize canonical analyzer song metadata")
    parser.add_argument("song_path", type=str, help="Path to the source song file")
    parser.add_argument("--meta-path", type=str, default=META_PATH, help="Path to the analyzer meta root")
    args = parser.parse_args()
    payload = init_song_payload(args.song_path, args.meta_path)
    print(f"Initialized {Path(payload['info_file']).name} for {payload['song']}: {payload['info_file']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())