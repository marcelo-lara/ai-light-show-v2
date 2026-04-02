from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.http_api import create_app


def test_http_api_queue_crud_and_playback_lock(tmp_path: Path) -> None:
    queue_path = tmp_path / "queue.json"
    app = create_app(queue_path=queue_path, worker_enabled=False)

    with TestClient(app) as client:
        task_types = client.get("/task-types")
        assert task_types.status_code == 200
        catalog = task_types.json()["task_types"]
        assert any(item["value"] == "generate-md" for item in catalog)
        assert any(item["value"] == "init-song" for item in catalog)

        task_type = client.get("/task-types/generate-md")
        assert task_type.status_code == 200
        assert task_type.json()["task_type"]["produces"] == ["song markdown summary"]

        status = client.get("/queue/status")
        assert status.status_code == 200
        assert status.json()["summary"]["queued"] == 0
        assert status.json()["polling"] is False

        created = client.post(
            "/queue/items",
            json={"task_type": "generate-md", "params": {"song_path": "/tmp/Test Song.mp3", "meta_path": "/tmp/meta"}},
        )
        assert created.status_code == 200
        item_id = created.json()["item_id"]

        listed = client.get("/queue/items").json()["items"]
        assert len(listed) == 1
        assert listed[0]["item_id"] == item_id
        assert listed[0]["status"] == "queued"

        executed = client.post(f"/queue/items/{item_id}/execute")
        assert executed.status_code == 200
        assert executed.json()["item"]["status"] == "pending"

        locked = client.post("/runtime/playback-lock", json={"locked": True})
        assert locked.status_code == 200
        assert locked.json()["playback_locked"] is True


def test_http_api_full_artifact_playlist_endpoints(tmp_path: Path) -> None:
    queue_path = tmp_path / "queue.json"
    app = create_app(queue_path=queue_path, worker_enabled=False)
    song_path = tmp_path / "songs" / "Alpha.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()

    with TestClient(app) as client:
        metadata = client.get("/playlists")
        assert metadata.status_code == 200
        assert metadata.json()["playlists"][0]["value"] == "full-artifact"

        full_metadata = client.get("/playlists/full-artifact/metadata")
        assert full_metadata.status_code == 200
        assert full_metadata.json()["playlist"]["variants"][0]["value"] == "full-artifact-analyzer"

        built = client.get(
            "/playlists/full-artifact",
            params={"song_path": str(song_path), "meta_path": str(tmp_path / "meta"), "device": "cpu"},
        )
        assert built.status_code == 200
        playlist = built.json()["playlist"]
        assert playlist["playlist"] == "full-artifact-analyzer"
        assert playlist["tasks"][0]["task_type"] == "init-song"

        from src.api import routes as routes_module

        original_execute = routes_module.execute_full_artifact_playlist
        routes_module.execute_full_artifact_playlist = lambda song_path, meta_path, device=None: {
            "playlist": "full-artifact-analyzer",
            "song": Path(song_path).name,
            "uses_moises": False,
            "status": "completed",
            "tasks": [{"task_type": "init-song"}, {"task_type": "split-stems"}],
            "results": [{"task_type": "init-song", "ok": True, "value": {"info_file": str(Path(meta_path) / Path(song_path).stem / "info.json")}}],
        }
        executed = client.post(
            "/playlists/full-artifact/execute",
            json={"song_path": str(song_path), "meta_path": str(tmp_path / "meta"), "device": "cpu"},
        )
        routes_module.execute_full_artifact_playlist = original_execute
        assert executed.status_code == 200
        result = executed.json()["result"]
        assert result["playlist"] == "full-artifact-analyzer"
        assert result["status"] == "completed"
        assert result["results"][0]["task_type"] == "init-song"


def test_http_api_queue_full_artifact_playlist(tmp_path: Path) -> None:
    queue_path = tmp_path / "queue.json"
    app = create_app(queue_path=queue_path, worker_enabled=False)
    song_path = tmp_path / "songs" / "Alpha.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()

    with TestClient(app) as client:
        queued = client.post(
            "/queue/playlists/full-artifact",
            json={"song_path": str(song_path), "meta_path": str(tmp_path / "meta"), "device": "cpu", "activate": True},
        )
        assert queued.status_code == 200
        payload = queued.json()
        assert payload["playlist"]["playlist"] == "full-artifact-analyzer"
        assert [item["task_type"] for item in payload["scheduled"]][:4] == ["init-song", "split-stems", "beat-finder", "find_sections"]
        assert all(item["status"] == "pending" for item in payload["scheduled"])


def test_http_api_full_artifact_playlist_detects_moises_song(tmp_path: Path) -> None:
    queue_path = tmp_path / "queue.json"
    app = create_app(queue_path=queue_path, worker_enabled=False)
    song_path = tmp_path / "songs" / "Beta.mp3"
    song_path.parent.mkdir(parents=True)
    song_path.touch()
    moises_dir = tmp_path / "meta" / "Beta" / "moises"
    moises_dir.mkdir(parents=True)
    (moises_dir / "chords.json").write_text(json.dumps([{"curr_beat_time": 1.0, "beat_num": 1, "bar_num": 1, "bass": "C", "chord_basic_pop": "C"}]), encoding="utf-8")

    with TestClient(app) as client:
        built = client.get(
            "/playlists/full-artifact",
            params={"song_path": str(song_path), "meta_path": str(tmp_path / "meta"), "device": "cpu"},
        )
        assert built.status_code == 200
        playlist = built.json()["playlist"]
        assert playlist["playlist"] == "full-artifact-moises"
        assert playlist["tasks"][2]["task_type"] == "import-moises"