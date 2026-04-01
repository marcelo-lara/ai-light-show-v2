from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from backend.models.cues import CueSheet
from models.song import resolve_meta_root
from backend.store.state import StateManager


CHASER_ID = "downbeats_and_beats"


def _state_manager() -> StateManager:
    workspace_root = Path(__file__).resolve().parents[1]
    backend_path = workspace_root / "backend"
    songs_path = Path("/app/songs") if Path("/app/songs").exists() else backend_path / "songs"
    cues_path = Path("/app/cues") if Path("/app/cues").exists() else backend_path / "cues"
    meta_path = resolve_meta_root(backend_path)
    return StateManager(backend_path, songs_path, cues_path, meta_path)


@pytest.mark.asyncio
async def test_chaser_preview_starts_and_cleans_up():
    sm = _state_manager()
    await sm.load_fixtures(sm.backend_path / "fixtures" / "fixtures.json")
    sm.current_song = cast(Any, SimpleNamespace(song_id="test_preview", meta=SimpleNamespace(bpm=600.0)))

    started = await sm.start_preview_chaser(CHASER_ID, start_time_ms=0.0, repetitions=1, request_id="preview-1")

    assert started["ok"] is True
    assert started["chaser_id"] == CHASER_ID
    assert sm.preview_chaser_active is True

    await sm.cancel_preview_chaser()

    assert sm.preview_chaser_active is False
    assert sm.preview_chaser_task is None
    assert sm.preview_chaser_request_id is None


@pytest.mark.asyncio
async def test_chaser_preview_rejects_while_playing():
    sm = _state_manager()
    await sm.load_fixtures(sm.backend_path / "fixtures" / "fixtures.json")
    sm.current_song = cast(Any, SimpleNamespace(song_id="test_preview", meta=SimpleNamespace(bpm=120.0)))
    sm.is_playing = True

    started = await sm.start_preview_chaser(CHASER_ID, start_time_ms=0.0, repetitions=1)

    assert started["ok"] is False
    assert started["reason"] == "playback_active"


@pytest.mark.asyncio
async def test_chaser_apply_persists_chaser_rows():
    sm = _state_manager()
    await sm.load_fixtures(sm.backend_path / "fixtures" / "fixtures.json")
    sm.current_song = cast(Any, SimpleNamespace(song_id="test_chaser_dedup", meta=SimpleNamespace(bpm=120.0)))
    sm.cue_sheet = CueSheet(song_filename="test_chaser_dedup", entries=[])
    cue_file = sm.backend_path / "cues" / "test_chaser_dedup.json"

    try:
        first = await sm.apply_chaser(CHASER_ID, start_time_ms=0.0, repetitions=1)
        second = await sm.apply_chaser(CHASER_ID, start_time_ms=50.0, repetitions=2)

        assert first["ok"] is True
        assert second["ok"] is True
        assert first["entry"]["chaser_id"] == CHASER_ID
        assert second["entry"]["chaser_id"] == CHASER_ID
        assert first["entry"]["data"] == {"repetitions": 1}
        assert second["entry"]["data"] == {"repetitions": 2}
        assert len(sm.cue_sheet.entries) == 1
        assert sm.cue_sheet.entries[0].chaser_id == CHASER_ID
        assert sm.cue_sheet.entries[0].time == 0.05
        assert sm.cue_sheet.entries[0].data == {"repetitions": 2}
    finally:
        if cue_file.exists():
            cue_file.unlink()
