import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analyzer"))

from src.runtime.app import create_app


def test_http_api_queue_crud_and_playback_lock(tmp_path: Path):
    queue_path = tmp_path / "queue.json"
    app = create_app(queue_path=queue_path, worker_enabled=False)

    with TestClient(app) as client:
        task_types = client.get("/task-types")
        assert task_types.status_code == 200
        catalog = task_types.json()["task_types"]
        assert any(item["value"] == "generate-md" for item in catalog)
        assert any(item["value"] == "find_sections" for item in catalog)

        status = client.get("/queue/status")
        assert status.status_code == 200
        assert status.json()["summary"]["queued"] == 0
        assert status.json()["polling"] is False

        created = client.post(
            "/queue/items",
            json={
                "task_type": "generate-md",
                "params": {"song_path": "/tmp/Test Song.mp3", "meta_path": "/tmp/meta"},
            },
        )
        assert created.status_code == 200
        item_id = created.json()["item_id"]

        listed = client.get("/queue/items").json()["items"]
        assert len(listed) == 1
        assert listed[0]["item_id"] == item_id
        assert listed[0]["status"] == "queued"

        fetched = client.get(f"/queue/items/{item_id}")
        assert fetched.status_code == 200
        assert fetched.json()["item"]["task_type"] == "generate-md"

        executed = client.post(f"/queue/items/{item_id}/execute")
        assert executed.status_code == 200
        assert executed.json()["item"]["status"] == "pending"

        locked = client.post("/runtime/playback-lock", json={"locked": True})
        assert locked.status_code == 200
        assert locked.json()["playback_locked"] is True
        assert locked.json()["summary"]["pending"] == 1

        deleted = client.delete(f"/queue/items/{item_id}")
        assert deleted.status_code == 200
        assert client.get("/queue/items").json()["items"] == []


def test_http_api_clears_queue_on_startup(tmp_path: Path):
    queue_path = tmp_path / "queue.json"
    queue_path.write_text(
        '{"items":[{"item_id":"one","task_type":"generate-md","params":{"song_path":"/tmp/A.mp3"},"status":"failed","created_at":"2026-03-30T00:00:00Z","updated_at":"2026-03-30T00:00:00Z","queued_at":"2026-03-30T00:00:00Z","pending_at":"2026-03-30T00:00:00Z","started_at":"2026-03-30T00:00:00Z","finished_at":"2026-03-30T00:01:00Z","progress":null,"last_result":null,"error":"Interrupted before completion"}]}'
        ,
        encoding="utf-8",
    )
    app = create_app(queue_path=queue_path, worker_enabled=False)

    with TestClient(app) as client:
        listed = client.get("/queue/items")
        assert listed.status_code == 200
        items = listed.json()["items"]
        assert items == []
        status = client.get("/queue/status")
        assert status.status_code == 200
        assert status.json()["summary"]["queued"] == 0
        assert status.json()["summary"]["pending"] == 0
        assert status.json()["summary"]["running"] == 0