from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from backend.models.cues import CueSheet
from backend.store.state import StateManager


CHASER_NAME = "Downbeat plus two beats"


def _state_manager() -> StateManager:
    workspace_root = Path(__file__).resolve().parents[1]
    backend_path = workspace_root / "backend"
    songs_path = Path("/app/songs") if Path("/app/songs").exists() else backend_path / "songs"
    cues_path = Path("/app/cues") if Path("/app/cues").exists() else backend_path / "cues"
    meta_path = Path("/app/meta") if Path("/app/meta").exists() else backend_path / "meta"
    return StateManager(backend_path, songs_path, cues_path, meta_path)


@pytest.mark.asyncio
async def test_chaser_preview_starts_and_cleans_up():
    sm = _state_manager()
    await sm.load_fixtures(sm.backend_path / "fixtures" / "fixtures.json")
    sm.current_song = cast(Any, SimpleNamespace(song_id="test_preview", meta=SimpleNamespace(bpm=600.0)))

    started = await sm.start_preview_chaser(CHASER_NAME, start_time_ms=0.0, repetitions=1, request_id="preview-1")

    assert started["ok"] is True
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

    started = await sm.start_preview_chaser(CHASER_NAME, start_time_ms=0.0, repetitions=1)

    assert started["ok"] is False
    assert started["reason"] == "playback_active"


@pytest.mark.asyncio
async def test_chaser_apply_upsert_prevents_duplicate_fixture_time():
    sm = _state_manager()
    await sm.load_fixtures(sm.backend_path / "fixtures" / "fixtures.json")
    sm.current_song = cast(Any, SimpleNamespace(song_id="test_chaser_dedup", meta=SimpleNamespace(bpm=120.0)))
    sm.cue_sheet = CueSheet(song_filename="test_chaser_dedup", entries=[])
    cue_file = sm.backend_path / "cues" / "test_chaser_dedup.json"

    try:
        first = await sm.apply_chaser(CHASER_NAME, start_time_ms=0.0, repetitions=1)
        second = await sm.apply_chaser(CHASER_NAME, start_time_ms=0.0, repetitions=1)

        assert first["ok"] is True
        assert second["ok"] is True
        assert second["generated"] == 0
        assert second["replaced"] == first["entries"]
        assert len(sm.cue_sheet.entries) == first["entries"]
    finally:
        if cue_file.exists():
            cue_file.unlink()
