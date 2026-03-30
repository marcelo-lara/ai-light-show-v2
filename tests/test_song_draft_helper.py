from pathlib import Path

import pytest

from models.song import Song
from services.cue_helpers.song_draft import generate_song_draft
from store.state import StateManager


@pytest.mark.asyncio
async def test_generate_song_draft_uses_analysis_and_live_rig() -> None:
    workspace_root = Path(__file__).resolve().parents[1]
    backend_path = workspace_root / "backend"
    songs_path = Path("/app/songs") if Path("/app/songs").exists() else backend_path / "songs"
    cues_path = Path("/app/cues") if Path("/app/cues").exists() else backend_path / "cues"
    meta_path = Path("/app/meta") if Path("/app/meta").exists() else backend_path / "meta"
    state_manager = StateManager(backend_path, songs_path, cues_path, meta_path)
    await state_manager.load_fixtures(backend_path / "fixtures" / "fixtures.json")
    await state_manager.load_pois(backend_path / "fixtures" / "pois.json")

    song = Song(song_id="Yonaka - Seize the Power", base_dir=str(meta_path))
    entries = generate_song_draft(song, list(state_manager.fixtures), await state_manager.get_pois(), state_manager._fixture_supported_effects)

    assert entries
    assert any(entry["effect"] == "orbit" for entry in entries)
    assert any(entry["fixture_id"].startswith("parcan_") and entry["effect"] == "flash" for entry in entries)
    fixture_ids = {fixture.id for fixture in state_manager.fixtures}
    assert all(entry["fixture_id"] in fixture_ids for entry in entries)