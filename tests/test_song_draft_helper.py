from pathlib import Path

import pytest

from models.song import Song, resolve_meta_root, resolve_songs_root
from services.cue_helpers.song_draft import generate_song_draft
from store.state import StateManager

TEST_SONG = "Cinderella - Ella Lee"


def test_resolve_meta_root_prefers_local_data_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    backend_path = tmp_path / "backend"
    data_output = tmp_path / "data" / "output"
    backend_path.mkdir()
    data_output.mkdir(parents=True)
    monkeypatch.setattr("models.song.meta_root.DOCKER_META_ROOT", tmp_path / "missing-app-meta")

    assert resolve_meta_root(backend_path) == data_output


@pytest.mark.asyncio
async def test_generate_song_draft_uses_analysis_and_live_rig() -> None:
    workspace_root = Path(__file__).resolve().parents[1]
    backend_path = workspace_root / "backend"
    songs_path = resolve_songs_root(backend_path)
    cues_path = Path("/app/cues") if Path("/app/cues").exists() else backend_path / "cues"
    meta_path = resolve_meta_root(backend_path)
    state_manager = StateManager(backend_path, songs_path, cues_path, meta_path)
    await state_manager.load_fixtures(backend_path / "fixtures" / "fixtures.json")
    await state_manager.load_pois(backend_path / "fixtures" / "pois.json")

    song = Song(song_id=TEST_SONG, base_dir=str(meta_path))
    entries = generate_song_draft(song, list(state_manager.fixtures), await state_manager.get_pois(), state_manager._fixture_supported_effects)

    assert entries
    assert any(entry["effect"] == "orbit" for entry in entries)
    assert any(entry["fixture_id"].startswith("parcan_") and entry["effect"] == "flash" for entry in entries)
    fixture_ids = {fixture.id for fixture in state_manager.fixtures}
    assert all(entry["fixture_id"] in fixture_ids for entry in entries)


def test_generate_song_draft_reports_missing_artifacts(tmp_path: Path) -> None:
    meta_path = tmp_path / "meta"
    song_dir = meta_path / "Test Song"
    song_dir.mkdir(parents=True)
    info_path = song_dir / "info.json"
    info_path.write_text('{"title": "Test Song", "artist": "Test Artist", "duration": 10, "bpm": 120, "artifacts": {}}', encoding="utf-8")
    (song_dir / "beats.json").write_text('[{"time": 0.0, "beat": 1, "bar": 1, "type": "downbeat"}]', encoding="utf-8")
    (song_dir / "sections.json").write_text('[{"label": "Intro", "start": 0.0, "end": 10.0}]', encoding="utf-8")

    song = Song(song_id="Test Song", base_dir=str(meta_path))
    with pytest.raises(ValueError, match="features_unavailable") as exc_info:
        generate_song_draft(song, [], [], lambda _fixture: set())

    assert getattr(exc_info.value, "missing_artifacts") == [
        {"artifact": "features_file", "path": str(song_dir / "features.json")},
        {"artifact": "hints_file", "path": str(song_dir / "hints.json")},
    ]