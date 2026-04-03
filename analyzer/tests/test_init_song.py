from __future__ import annotations

import json
from pathlib import Path

from src.tasks.init_song import init_song_payload


def test_init_song_creates_minimal_info_root(tmp_path: Path) -> None:
    song_path = tmp_path / "songs" / "Alpha.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()

    payload = init_song_payload(song_path, tmp_path / "meta")

    info_file = Path(payload["info_file"])
    assert info_file.exists()
    assert json.loads(info_file.read_text(encoding="utf-8")) == {
        "song_name": "Alpha",
        "song_path": str(song_path.resolve()),
        "bpm": 0.0,
        "duration": 0.0,
        "artifacts": {},
    }


def test_init_song_does_not_overwrite_existing_info(tmp_path: Path) -> None:
    song_path = tmp_path / "songs" / "Alpha.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    meta_root = tmp_path / "meta"
    info_file = meta_root / "Alpha" / "info.json"
    info_file.parent.mkdir(parents=True)
    info_file.write_text(
        json.dumps({"song_name": "Alpha", "song_path": str(song_path.resolve()), "artifacts": {}, "custom": True}, indent=2),
        encoding="utf-8",
    )

    payload = init_song_payload(song_path, meta_root)

    assert payload["info_file"] == str(info_file)
    assert json.loads(info_file.read_text(encoding="utf-8"))["custom"] is True