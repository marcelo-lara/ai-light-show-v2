import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analyzer"))

from src import task_queue_api
from src.task_queue_store import clear_items


def test_add_list_execute_and_remove_queue_item(tmp_path: Path):
    queue_path = tmp_path / "queue.json"

    item_id = task_queue_api.add_item(
        "generate-md",
        {"song_path": "/tmp/Test Song.mp3", "meta_path": "/tmp/meta"},
        queue_path=queue_path,
    )

    items = task_queue_api.list_items(queue_path)
    assert len(items) == 1
    assert items[0]["item_id"] == item_id
    assert items[0]["status"] == "queued"

    updated = task_queue_api.execute_item(item_id, queue_path)
    assert updated is not None
    assert updated["status"] == "pending"
    assert task_queue_api.remove_item(item_id, queue_path) is True
    assert task_queue_api.list_items(queue_path) == []


def test_process_queue_runs_pending_item_and_persists_progress(tmp_path: Path, monkeypatch):
    queue_path = tmp_path / "queue.json"
    item_id = task_queue_api.add_item(
        "essentia-analysis",
        {"song_path": "/tmp/Test Song.mp3", "meta_path": "/tmp/meta"},
        queue_path=queue_path,
    )
    task_queue_api.execute_item(item_id, queue_path)

    def fake_run_task(task_type: str, params: dict, progress_callback=None):
        if progress_callback is not None:
            progress_callback(
                {
                    "task_type": task_type,
                    "stage": "Loudness & Envelope",
                    "step_current": 12,
                    "step_total": 25,
                    "message": "essentia-analysis [12/25] Loudness & Envelope",
                    "part_name": "mix",
                }
            )
        return {"ok": True, "task_type": task_type, "song": "Test Song.mp3", "params": params, "value": {"artifact": "ok"}}

    monkeypatch.setattr(task_queue_api, "run_task", fake_run_task)

    completed = task_queue_api.process_queue(queue_path)
    payload = json.loads(queue_path.read_text(encoding="utf-8"))
    item = payload["items"][0]

    assert completed is not None
    assert item["status"] == "complete"
    assert item["progress"]["stage"] == "Loudness & Envelope"
    assert item["progress"]["step_current"] == 12
    assert item["progress"]["step_total"] == 25
    assert item["last_result"]["ok"] is True


def test_process_queue_returns_none_when_running_item_exists(tmp_path: Path):
    queue_path = tmp_path / "queue.json"
    queue_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "item_id": "one",
                        "task_type": "generate-md",
                        "params": {"song_path": "/tmp/A.mp3"},
                        "status": "running",
                        "created_at": "2026-03-30T00:00:00Z",
                        "updated_at": "2026-03-30T00:00:00Z",
                        "queued_at": "2026-03-30T00:00:00Z",
                        "pending_at": "2026-03-30T00:00:00Z",
                        "started_at": "2026-03-30T00:00:00Z",
                        "finished_at": None,
                        "progress": None,
                        "last_result": None,
                        "error": None,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    items = task_queue_api.list_items(queue_path)

    assert items[0]["status"] == "running"
    assert items[0]["error"] is None
    assert task_queue_api.process_queue(queue_path) is None


def test_clear_items_empties_queue_file(tmp_path: Path):
    queue_path = tmp_path / "queue.json"
    queue_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "item_id": "running-one",
                        "task_type": "generate-md",
                        "params": {"song_path": "/tmp/A.mp3"},
                        "status": "running",
                        "created_at": "2026-03-30T00:00:00Z",
                        "updated_at": "2026-03-30T00:00:00Z",
                        "queued_at": "2026-03-30T00:00:00Z",
                        "pending_at": "2026-03-30T00:00:00Z",
                        "started_at": "2026-03-30T00:00:00Z",
                        "finished_at": None,
                        "progress": {"stage": "Analyzing"},
                        "last_result": None,
                        "error": None,
                    },
                    {
                        "item_id": "failed-one",
                        "task_type": "generate-md",
                        "params": {"song_path": "/tmp/B.mp3"},
                        "status": "failed",
                        "created_at": "2026-03-30T00:00:00Z",
                        "updated_at": "2026-03-30T00:00:00Z",
                        "queued_at": "2026-03-30T00:00:00Z",
                        "pending_at": "2026-03-30T00:00:00Z",
                        "started_at": "2026-03-30T00:00:00Z",
                        "finished_at": "2026-03-30T00:10:00Z",
                        "progress": None,
                        "last_result": None,
                        "error": "Interrupted before completion",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    items = clear_items(queue_path)

    assert items == []
    assert task_queue_api.list_items(queue_path) == []


def test_add_item_rejects_unknown_task_type(tmp_path: Path):
    queue_path = tmp_path / "queue.json"

    try:
        task_queue_api.add_item("unknown-task", {"song_path": "/tmp/Test Song.mp3"}, queue_path=queue_path)
    except ValueError as exc:
        assert str(exc) == "Unsupported task_type: unknown-task"
    else:
        raise AssertionError("Expected ValueError for unsupported task_type")