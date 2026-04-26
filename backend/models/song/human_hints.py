from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from .analysis_files import resolve_data_root


def resolve_human_hints_path(meta_root: Path, song_id: str) -> Path:
    return resolve_data_root(meta_root) / "reference" / song_id / "human" / "human_hints.json"


class HumanHints:
    def __init__(self, meta_root: Path, song_id: str):
        self.song_id = song_id
        self.path = resolve_human_hints_path(meta_root, song_id)
        self.song_name = song_id
        self.human_hints: List[Dict[str, Any]] = []
        self.dirty = False
        self.file_exists = False
        self._load_sync()

    def _load_sync(self) -> None:
        self.file_exists = self.path.exists()
        if not self.file_exists:
            self.song_name = self.song_id
            self.human_hints = []
            self.dirty = False
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
        self.song_name = str(payload.get("song_name") or self.song_id)
        rows = payload.get("human_hints") if isinstance(payload, dict) else []
        self.human_hints = [self._normalize_hint(row) for row in rows if isinstance(row, dict)]
        self.human_hints.sort(key=lambda item: (item["start_time"], item["end_time"], item["id"]))
        self.dirty = False

    def _normalize_hint(self, row: Dict[str, Any]) -> Dict[str, Any]:
        start_time = self._to_number(row.get("start_time"))
        end_time = max(start_time, self._to_number(row.get("end_time"), start_time))
        return {
            "id": str(row.get("id") or self._next_id()).strip(),
            "start_time": start_time,
            "end_time": end_time,
            "title": str(row.get("title") or "").strip(),
            "summary": str(row.get("summary") or "").strip(),
            "lighting_hint": str(row.get("lighting_hint") or "").strip(),
        }

    def _next_id(self) -> str:
        seen = 0
        for row in self.human_hints:
            match = re.fullmatch(r"ui_(\d+)", str(row.get("id") or ""))
            if match:
                seen = max(seen, int(match.group(1)))
        return f"ui_{seen + 1:03d}"

    @staticmethod
    def _to_number(value: Any, fallback: float = 0.0) -> float:
        try:
            picked = float(value)
        except Exception:
            return fallback
        return picked if picked >= 0.0 else fallback

    def status(self) -> Dict[str, bool]:
        return {"dirty": self.dirty, "saved": not self.dirty, "file_exists": self.file_exists}

    def list(self) -> List[Dict[str, Any]]:
        return [dict(row) for row in self.human_hints]

    def create(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        hint = self._normalize_hint({**payload, "id": self._next_id()})
        self.human_hints.append(hint)
        self.human_hints.sort(key=lambda item: (item["start_time"], item["end_time"], item["id"]))
        self.dirty = True
        return dict(hint)

    def update(self, hint_id: str, patch: Dict[str, Any]) -> Dict[str, Any] | None:
        for index, row in enumerate(self.human_hints):
            if row.get("id") != hint_id:
                continue
            updated = self._normalize_hint({**row, **patch, "id": hint_id})
            self.human_hints[index] = updated
            self.human_hints.sort(key=lambda item: (item["start_time"], item["end_time"], item["id"]))
            self.dirty = True
            return dict(updated)
        return None

    def delete(self, hint_id: str) -> bool:
        original = len(self.human_hints)
        self.human_hints = [row for row in self.human_hints if row.get("id") != hint_id]
        self.dirty = len(self.human_hints) != original
        return self.dirty

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"song_name": self.song_name, "human_hints": self.human_hints}, indent=2) + "\n", encoding="utf-8")
        self.file_exists = True
        self.dirty = False