from pathlib import Path

import pytest

from store.state import StateManager


@pytest.mark.asyncio
async def test_preview_start_wait_and_cancel_lifecycle():
    workspace_root = Path(__file__).resolve().parents[1]
    backend_path = workspace_root / "backend"

    songs_path = Path("/app/songs") if Path("/app/songs").exists() else backend_path / "songs"
    cues_path = Path("/app/cues") if Path("/app/cues").exists() else backend_path / "cues"
    meta_path = Path("/app/meta") if Path("/app/meta").exists() else backend_path / "meta"

    sm = StateManager(backend_path, songs_path, cues_path, meta_path)
    await sm.load_fixtures(backend_path / "fixtures" / "fixtures.json")

    fixture_id = "parcan_l"

    started = await sm.start_preview_effect(
        fixture_id=fixture_id,
        effect="flash",
        duration=0.05,
        data={},
        request_id="preview-1",
    )
    assert started["ok"] is True
    assert started["requestId"] == "preview-1"
    assert sm.preview_active is True

    await sm.wait_for_preview_end("preview-1")
    assert sm.preview_active is False
    assert sm.preview_task is None

    started = await sm.start_preview_effect(
        fixture_id=fixture_id,
        effect="flash",
        duration=1.0,
        data={},
        request_id="preview-2",
    )
    assert started["ok"] is True
    assert sm.preview_active is True

    cancelled = await sm.cancel_preview()
    assert cancelled is True
    assert sm.preview_active is False
    assert sm.preview_task is None
