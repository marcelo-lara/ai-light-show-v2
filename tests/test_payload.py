from pathlib import Path

import pytest

from api.state.build_frontend_state import build_frontend_state
from api.state.fixtures import build_fixtures_payload
from store.state import StateManager
from api.websocket import WebSocketManager


@pytest.mark.asyncio
async def test_fixture_payload_shape():
    workspace_root = Path(__file__).resolve().parents[1]
    backend_path = workspace_root / "backend"

    songs_path = Path("/app/songs") if Path("/app/songs").exists() else backend_path / "songs"
    cues_path = Path("/app/cues") if Path("/app/cues").exists() else backend_path / "cues"
    meta_path = Path("/app/meta") if Path("/app/meta").exists() else backend_path / "meta"

    sm = StateManager(backend_path, songs_path, cues_path, meta_path)
    await sm.load_fixtures(backend_path / "fixtures" / "fixtures.json")

    # For this serialization test we do not need concrete service behavior.
    wm = WebSocketManager(sm, object(), object())

    universe = bytearray(512)
    payload = build_fixtures_payload(wm, universe)
    assert isinstance(payload, dict)
    assert len(payload) > 0
    fixture = next(iter(payload.values()))
    assert "id" in fixture
    assert "values" in fixture
    assert "meta_channels" in fixture

    parcan = payload.get("parcan_l")
    assert parcan is not None
    assert parcan["values"].get("rgb") == "#000000"
    assert [effect["id"] for effect in parcan["supported_effects"]] == ["blackout", "color_fade", "fade_in", "fade_out", "flash", "full", "set_channels", "strobe"]
    flash = next(effect for effect in parcan["supported_effects"] if effect["id"] == "flash")
    assert flash["tags"] == ["spike", "accent", "hard", "short"]
    assert "description" in flash
    assert "schema" in flash

    mover = payload.get("head_el150")
    assert mover is not None
    assert [effect["id"] for effect in mover["supported_effects"]] == [
        "blackout",
        "fade_in",
        "fade_out",
        "flash",
        "full",
        "move_to",
        "move_to_poi",
        "orbit",
        "set_channels",
        "strobe",
        "sweep",
    ]
    sweep = next(effect for effect in mover["supported_effects"] if effect["id"] == "sweep")
    assert sweep["tags"] == ["movement", "tension", "long", "soft"]


@pytest.mark.asyncio
async def test_frontend_state_includes_chasers_payload():
    workspace_root = Path(__file__).resolve().parents[1]
    backend_path = workspace_root / "backend"

    songs_path = Path("/app/songs") if Path("/app/songs").exists() else backend_path / "songs"
    cues_path = Path("/app/cues") if Path("/app/cues").exists() else backend_path / "cues"
    meta_path = Path("/app/meta") if Path("/app/meta").exists() else backend_path / "meta"

    sm = StateManager(backend_path, songs_path, cues_path, meta_path)
    await sm.load_fixtures(backend_path / "fixtures" / "fixtures.json")

    wm = WebSocketManager(sm, object(), object())
    payload = await build_frontend_state(wm)

    chasers = payload.get("chasers")
    assert isinstance(chasers, list)
    if chasers:
        first = chasers[0]
        assert "name" in first
        assert "description" in first
        assert "effects" in first


@pytest.mark.asyncio
async def test_frontend_state_includes_parameterized_cue_helpers():
    workspace_root = Path(__file__).resolve().parents[1]
    backend_path = workspace_root / "backend"

    songs_path = Path("/app/songs") if Path("/app/songs").exists() else backend_path / "songs"
    cues_path = Path("/app/cues") if Path("/app/cues").exists() else backend_path / "cues"
    meta_path = Path("/app/meta") if Path("/app/meta").exists() else backend_path / "meta"

    sm = StateManager(backend_path, songs_path, cues_path, meta_path)
    await sm.load_fixtures(backend_path / "fixtures" / "fixtures.json")

    wm = WebSocketManager(sm, object(), object())
    payload = await build_frontend_state(wm)

    helpers = payload.get("cue_helpers")
    assert isinstance(helpers, list)
    echoes = next((helper for helper in helpers if helper.get("id") == "parcan_echoes"), None)
    assert echoes is not None
    assert echoes["mode"] == "parameterized"
    assert any(param["name"] == "start_time_ms" for param in echoes["parameters"])
