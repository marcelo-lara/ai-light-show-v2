from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

QUEUE_FILE_PATH = Path(__file__).resolve().parents[2] / "temp_files" / "queue.json"
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
        return payload.get("items", [])


def clear_items(queue_path: Path = QUEUE_FILE_PATH) -> list[dict[str, Any]]:
    with QUEUE_LOCK:
        save_items([], queue_path)
        return []


def save_items(items: list[dict[str, Any]], queue_path: Path = QUEUE_FILE_PATH) -> None:
    with QUEUE_LOCK:
        ensure_queue_file(queue_path)
        payload = {"items": items}
        queue_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
