from fastapi.testclient import TestClient

import backend.main as backend_main
from services.artnet import ArtNetService
from services.song_service import SongService


def test_backend_vulnerabilities_route_lists_known_backend_risks(monkeypatch):
    async def _noop_async(*_args, **_kwargs):
        return None

    monkeypatch.setattr(backend_main, "run_startup_blue_wipe", _noop_async)
    monkeypatch.setattr(SongService, "list_songs", lambda self: [])
    monkeypatch.setattr(ArtNetService, "start", _noop_async)
    monkeypatch.setattr(ArtNetService, "stop", _noop_async)
    monkeypatch.setattr(ArtNetService, "blackout", _noop_async)

    with TestClient(backend_main.app) as client:
        response = client.get("/vulnerabilities")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 3

    by_id = {item["id"]: item for item in payload["vulnerabilities"]}
    assert set(by_id) == {
        "unauthenticated_control_access",
        "permissive_cors_policy",
        "unauthenticated_static_asset_exposure",
    }
    assert by_id["unauthenticated_control_access"]["severity"] == "high"
    assert "/ws" in by_id["unauthenticated_control_access"]["surface"]
    assert "/vulnerabilities" in by_id["permissive_cors_policy"]["surface"]
    assert "/songs" in by_id["unauthenticated_static_asset_exposure"]["surface"]
