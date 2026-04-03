import json
from pathlib import Path

import pytest

from store.state import StateManager


@pytest.mark.asyncio
async def test_load_song_reloads_cue_sheet_and_rerenders_canvas(tmp_path: Path):
    backend_path = Path(__file__).resolve().parents[1] / "backend"
    songs_path = tmp_path / "songs"
    cues_path = tmp_path / "cues"
    meta_path = tmp_path / "meta"
    songs_path.mkdir()
    cues_path.mkdir()
    meta_path.mkdir()

    for song in ["alpha-song", "beta-song"]:
        (songs_path / f"{song}.mp3").write_bytes(b"")

    (cues_path / "alpha-song.json").write_text(json.dumps([
        {"time": 0.0, "fixture_id": "parcan_l", "effect": "set_channels", "duration": 0.0, "data": {"channels": {"red": 255}}},
    ]))
    (cues_path / "beta-song.json").write_text(json.dumps([
        {"time": 0.0, "fixture_id": "parcan_l", "effect": "set_channels", "duration": 0.0, "data": {"channels": {"blue": 255}}},
    ]))

    state_manager = StateManager(backend_path, songs_path, cues_path, meta_path)
    await state_manager.load_fixtures(backend_path / "fixtures" / "fixtures.json")

    await state_manager.load_song("alpha-song")
    first_entries = [entry.model_dump(exclude_none=True) for entry in state_manager.cue_sheet.entries]
    first_frame = bytes(state_manager.canvas.frame_view(0))

    await state_manager.load_song("beta-song")
    second_entries = [entry.model_dump(exclude_none=True) for entry in state_manager.cue_sheet.entries]
    second_frame = bytes(state_manager.canvas.frame_view(0))

    assert state_manager.current_song.song_id == "beta-song"
    assert state_manager.cue_sheet.song_filename == "beta-song"
    assert first_entries != second_entries
    assert first_frame != second_frame


@pytest.mark.asyncio
async def test_reload_cue_sheet_from_disk_rerenders_canvas(tmp_path: Path):
    backend_path = Path(__file__).resolve().parents[1] / "backend"
    songs_path = tmp_path / "songs"
    cues_path = tmp_path / "cues"
    meta_path = tmp_path / "meta"
    songs_path.mkdir()
    cues_path.mkdir()
    meta_path.mkdir()

    song = "alpha-song"
    (songs_path / f"{song}.mp3").write_bytes(b"")
    cue_path = cues_path / f"{song}.json"
    cue_path.write_text(json.dumps([
        {"time": 0.0, "fixture_id": "parcan_l", "effect": "set_channels", "duration": 0.0, "data": {"channels": {"red": 255}}},
    ]))

    state_manager = StateManager(backend_path, songs_path, cues_path, meta_path)
    await state_manager.load_fixtures(backend_path / "fixtures" / "fixtures.json")
    await state_manager.load_song(song)

    first_entries = [entry.model_dump(exclude_none=True) for entry in state_manager.cue_sheet.entries]
    first_frame = bytes(state_manager.canvas.frame_view(0))

    cue_path.write_text(json.dumps([
        {"time": 0.0, "fixture_id": "parcan_l", "effect": "set_channels", "duration": 0.0, "data": {"channels": {"blue": 255}}},
    ]))

    result = await state_manager.reload_cue_sheet_from_disk()

    second_entries = [entry.model_dump(exclude_none=True) for entry in state_manager.cue_sheet.entries]
    second_frame = bytes(state_manager.canvas.frame_view(0))

    assert result["ok"] is True
    assert result["song_filename"] == song
    assert result["count"] == 1
    assert first_entries != second_entries
    assert first_frame != second_frame