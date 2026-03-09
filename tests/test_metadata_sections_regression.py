import json
from pathlib import Path

import pytest

from models.song import Song, SongMetadata
from store.state import StateManager


@pytest.mark.asyncio
async def test_metadata_loader_and_section_persistence(tmp_path: Path):
    backend_path = tmp_path / "backend"
    songs_path = tmp_path / "songs"
    cues_path = tmp_path / "cues"
    meta_path = tmp_path / "meta"

    backend_path.mkdir(parents=True, exist_ok=True)
    songs_path.mkdir(parents=True, exist_ok=True)
    cues_path.mkdir(parents=True, exist_ok=True)
    (meta_path / "demo-song").mkdir(parents=True, exist_ok=True)

    meta_file = meta_path / "demo-song" / "demo-song.json"
    beats_file = meta_path / "demo-song" / "beats.json"

    with open(meta_file, "w") as handle:
        json.dump({
            "filename": "demo-song",
            "parts": {},
            "hints": {},
            "drums": {},
            "beat_tracking": {"tempo_bpm": 123},
            "artifacts": {"beats_file": "beats.json"},
        }, handle)

    with open(beats_file, "w") as handle:
        json.dump({
            "beats": [0.0, 0.5, 1.0, 1.5],
            "downbeats": [0.0, 2.0],
        }, handle)

    sm = StateManager(backend_path, songs_path, cues_path, meta_path)
    metadata = sm._load_song_metadata("demo-song")
    assert metadata.bpm == 123
    assert metadata.hints.get("beats") == [0.0, 0.5, 1.0, 1.5]
    assert metadata.hints.get("downbeats") == [0.0, 2.0]

    sm.current_song = Song(
        filename="demo-song",
        metadata=SongMetadata(filename="demo-song", parts={}, hints={}, drums={}),
        audioUrl=None,
    )

    result = await sm.save_song_sections([
        {"name": "Intro", "start": 0.0, "end": 10.0},
        {"name": "Verse", "start": 10.0, "end": 30.0},
    ])
    assert result["ok"] is True
    assert "Intro" in result["parts"]
    assert "Verse" in result["parts"]

    with open(meta_file, "r") as handle:
        persisted = json.load(handle)
    assert "parts" in persisted
    assert persisted["parts"]["Intro"] == [0.0, 10.0]
