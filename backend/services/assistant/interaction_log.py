from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AssistantInteractionLog:
    def __init__(self, log_dir: Path) -> None:
        self._log_dir = log_dir
        self._lock = asyncio.Lock()

    async def write(self, event: str, **payload: Any) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **payload,
        }
        async with self._lock:
            await asyncio.to_thread(self._append_line, record)

    def _append_line(self, record: dict[str, Any]) -> None:
        self._log_dir.mkdir(parents=True, exist_ok=True)
        log_path = self._log_dir / f"assistant-interactions-{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")