from pathlib import Path

import pytest

from api.state.build_frontend_state import build_frontend_state
from api.websocket import WebSocketManager
from models.song import resolve_meta_root, resolve_songs_root
from store.state import StateManager


@pytest.mark.asyncio
async def test_frontend_state_includes_analyzer_snapshot():
    workspace_root = Path(__file__).resolve().parents[1]
    backend_path = workspace_root / "backend"
    songs_path = resolve_songs_root(backend_path)
    cues_path = Path("/app/cues") if Path("/app/cues").exists() else backend_path / "cues"
    meta_path = resolve_meta_root(backend_path)

    state_manager = StateManager(backend_path, songs_path, cues_path, meta_path)
    await state_manager.load_fixtures(backend_path / "fixtures" / "fixtures.json")
    manager = WebSocketManager(state_manager, object(), object())
    manager.analyzer_service = type(
        "AnalyzerStub",
        (),
        {"snapshot": lambda self: {"available": True, "polling": True, "playback_locked": False, "items": [{"item_id": "item-1"}], "summary": {"queued": 1, "pending": 0, "running": 0, "complete": 0, "failed": 0}}},
    )()

    payload = await build_frontend_state(manager)

    assert payload["analyzer"]["available"] is True
    assert payload["analyzer"]["items"] == [{"item_id": "item-1"}]
    assert payload["analyzer"]["summary"]["queued"] == 1