from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from .task_dispatch import TASK_TYPES, run_task
from .task_queue_store import QUEUE_FILE_PATH, QUEUE_LOCK, load_items, now_iso, save_items


def list_items(queue_path: Path = QUEUE_FILE_PATH) -> list[dict[str, Any]]:
    with QUEUE_LOCK:
        return load_items(queue_path)


def get_item(item_id: str, queue_path: Path = QUEUE_FILE_PATH) -> dict[str, Any] | None:
    with QUEUE_LOCK:
        return next((item for item in load_items(queue_path) if item.get("item_id") == item_id), None)


def add_item(task_type: str, params: dict[str, Any], queue_path: Path = QUEUE_FILE_PATH) -> str:
    with QUEUE_LOCK:
        if task_type not in TASK_TYPES:
            raise ValueError(f"Unsupported task_type: {task_type}")
        timestamp = now_iso()
        item_id = uuid4().hex
        items = load_items(queue_path)
        items.append(
            {
                "item_id": item_id,
                "task_type": task_type,
                "params": params,
                "status": "queued",
                "created_at": timestamp,
                "updated_at": timestamp,
                "queued_at": timestamp,
                "pending_at": None,
                "started_at": None,
                "finished_at": None,
                "progress": None,
                "last_result": None,
                "error": None,
            }
        )
        save_items(items, queue_path)
        return item_id


def remove_item(item_id: str, queue_path: Path = QUEUE_FILE_PATH) -> bool:
    with QUEUE_LOCK:
        items = load_items(queue_path)
        remaining = [item for item in items if item.get("item_id") != item_id]
        if len(remaining) == len(items):
            return False
        save_items(remaining, queue_path)
        return True


def execute_item(item_id: str, queue_path: Path = QUEUE_FILE_PATH) -> dict[str, Any] | None:
    with QUEUE_LOCK:
        items = load_items(queue_path)
        timestamp = now_iso()
        for item in items:
            if item.get("item_id") != item_id:
                continue
            if item.get("status") != "queued":
                return None
            item["status"] = "pending"
            item["pending_at"] = timestamp
            item["updated_at"] = timestamp
            save_items(items, queue_path)
            return item
        return None


def run_next_pending(queue_path: Path = QUEUE_FILE_PATH) -> dict[str, Any] | None:
    with QUEUE_LOCK:
        items = load_items(queue_path)
        if any(item.get("status") == "running" for item in items):
            return None
        pending_item = next((item for item in items if item.get("status") == "pending"), None)
        if pending_item is None:
            return None
        started_at = now_iso()
        pending_item["status"] = "running"
        pending_item["started_at"] = started_at
        pending_item["updated_at"] = started_at
        save_items(items, queue_path)

        def on_progress(event: dict[str, Any]) -> None:
            with QUEUE_LOCK:
                pending_item["progress"] = event
                pending_item["updated_at"] = now_iso()
                save_items(items, queue_path)
            print(event["message"])

    try:
        result = run_task(pending_item["task_type"], pending_item["params"], progress_callback=on_progress)
        pending_item["status"] = "complete" if result.get("ok") else "failed"
        pending_item["last_result"] = result
        pending_item["error"] = None if result.get("ok") else f"Task returned no result for {pending_item['task_type']}"
    except Exception as exc:
        pending_item["status"] = "failed"
        pending_item["last_result"] = None
        pending_item["error"] = str(exc)

    with QUEUE_LOCK:
        finished_at = now_iso()
        pending_item["finished_at"] = finished_at
        pending_item["updated_at"] = finished_at
        save_items(items, queue_path)
        return pending_item


def process_queue(queue_path: Path = QUEUE_FILE_PATH) -> dict[str, Any] | None:
    return run_next_pending(queue_path)