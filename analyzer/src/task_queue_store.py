from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

QUEUE_FILE_PATH = Path(__file__).resolve().parents[1] / "temp_files" / "queue.json"
QUEUE_LOCK = RLock()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def ensure_queue_file(queue_path: Path = QUEUE_FILE_PATH) -> Path:
    with QUEUE_LOCK:
        queue_path.parent.mkdir(parents=True, exist_ok=True)
        if not queue_path.exists():
            queue_path.write_text('{"items": []}\n', encoding="utf-8")
    return queue_path


def load_items(queue_path: Path = QUEUE_FILE_PATH) -> list[dict[str, Any]]:
    with QUEUE_LOCK:
        payload = json.loads(ensure_queue_file(queue_path).read_text(encoding="utf-8"))
        items = payload.get("items", [])
        changed = False
        for item in items:
            if item.get("status") == "running":
                item["status"] = "failed"
                item["updated_at"] = now_iso()
                item["finished_at"] = item.get("finished_at") or item["updated_at"]
                item["error"] = "Interrupted before completion"
                changed = True
        if changed:
            save_items(items, queue_path)
        return items


def save_items(items: list[dict[str, Any]], queue_path: Path = QUEUE_FILE_PATH) -> None:
    with QUEUE_LOCK:
        ensure_queue_file(queue_path)
        payload = {"items": items}
        queue_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")