import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main as backend_main
from services.artnet import ArtNetService
from services.song_service import SongService


POI_ID = "piano"
FIXTURE_ID = "mini_beam_prism_l"


def _find_fixture_target(pois_payload, poi_id: str, fixture_id: str):
    for poi in pois_payload:
        if poi.get("id") != poi_id:
            continue
        fixtures = poi.get("fixtures") or {}
        if isinstance(fixtures, dict) and fixture_id in fixtures:
            return fixtures[fixture_id]
    return None


@pytest.mark.e2e_real_file
def test_ws_poi_update_persists_and_restores_real_file(request, monkeypatch):
    # Opt-in only: this test mutates repo-tracked data and restores it.
    selected_markexpr = (request.config.getoption("-m") or "").strip()
    if "e2e_real_file" not in selected_markexpr:
        pytest.skip("opt-in only; run with -m e2e_real_file")

    async def _noop_async(*_args, **_kwargs):
        return None

    # Keep this e2e test close to real websocket behavior while avoiding heavy startup work.
    monkeypatch.setattr(backend_main, "run_startup_blue_wipe", _noop_async)
    monkeypatch.setattr(SongService, "list_songs", lambda self: [])
    monkeypatch.setattr(ArtNetService, "start", _noop_async)
    monkeypatch.setattr(ArtNetService, "stop", _noop_async)
    monkeypatch.setattr(ArtNetService, "blackout", _noop_async)

    workspace_root = Path(__file__).resolve().parents[1]
    pois_path = workspace_root / "backend" / "fixtures" / "pois.json"
    original_bytes = pois_path.read_bytes()

    try:
        original_pois = json.loads(original_bytes.decode("utf-8"))
        original_target = _find_fixture_target(original_pois, POI_ID, FIXTURE_ID)
        assert original_target is not None, f"missing baseline target: poi={POI_ID}, fixture={FIXTURE_ID}"

        old_pan = int(original_target.get("pan", 0))
        old_tilt = int(original_target.get("tilt", 0))
        new_pan = (old_pan + 1111) % 65536
        new_tilt = (old_tilt + 2222) % 65536
        assert (new_pan, new_tilt) != (old_pan, old_tilt)

        with TestClient(backend_main.app) as client:
            with client.websocket_connect("/ws") as ws:
                initial = ws.receive_json()
                assert initial.get("type") == "snapshot"

                snapshot_target = _find_fixture_target(initial["state"].get("pois", []), POI_ID, FIXTURE_ID)
                assert snapshot_target is not None, "target POI/fixture missing from initial snapshot"

                ws.send_json(
                    {
                        "type": "intent",
                        "req_id": "e2e-poi-update-1",
                        "name": "poi.update_fixture_target",
                        "payload": {
                            "poi_id": POI_ID,
                            "fixture_id": FIXTURE_ID,
                            "pan": new_pan,
                            "tilt": new_tilt,
                        },
                    }
                )

                # Request an authoritative refresh and assert updated POI state over WS.
                ws.send_json({"type": "hello"})
                refreshed = ws.receive_json()
                assert refreshed.get("type") == "snapshot"

                refreshed_target = _find_fixture_target(refreshed["state"].get("pois", []), POI_ID, FIXTURE_ID)
                assert refreshed_target is not None
                assert int(refreshed_target.get("pan")) == new_pan
                assert int(refreshed_target.get("tilt")) == new_tilt

        persisted_pois = json.loads(pois_path.read_text(encoding="utf-8"))
        persisted_target = _find_fixture_target(persisted_pois, POI_ID, FIXTURE_ID)
        assert persisted_target is not None
        assert int(persisted_target.get("pan")) == new_pan
        assert int(persisted_target.get("tilt")) == new_tilt
    finally:
        pois_path.write_bytes(original_bytes)
        assert pois_path.read_bytes() == original_bytes
