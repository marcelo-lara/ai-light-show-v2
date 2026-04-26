from __future__ import annotations

from typing import Any, Dict

from models.song import HumanHints


class StateSongHintsMixin:
    def get_human_hints_payload(self) -> list[Dict[str, Any]]:
        if not self.human_hints:
            return []
        return self.human_hints.list()

    def get_human_hints_status(self) -> Dict[str, bool]:
        if not self.human_hints:
            return {"dirty": False, "saved": True, "file_exists": False}
        return self.human_hints.status()

    def load_human_hints(self, song_filename: str) -> None:
        self.human_hints = HumanHints(self.meta_path, song_filename)

    async def create_human_hint(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with self.lock:
            if not self.current_song:
                return {"ok": False, "reason": "no_song_loaded"}
            if not self.human_hints:
                self.load_human_hints(self.current_song.song_id)
            created = self.human_hints.create(payload)
            self.human_hints.save()
            return {"ok": True, "hint": created, "status": self.human_hints.status()}

    async def update_human_hint(self, hint_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        async with self.lock:
            if not self.human_hints:
                return {"ok": False, "reason": "no_song_loaded"}
            updated = self.human_hints.update(hint_id, patch)
            if not updated:
                return {"ok": False, "reason": "unknown_hint", "id": hint_id}
            self.human_hints.save()
            return {"ok": True, "hint": updated, "status": self.human_hints.status()}

    async def delete_human_hint(self, hint_id: str) -> Dict[str, Any]:
        async with self.lock:
            if not self.human_hints:
                return {"ok": False, "reason": "no_song_loaded"}
            deleted = self.human_hints.delete(hint_id)
            if not deleted:
                return {"ok": False, "reason": "unknown_hint", "id": hint_id}
            self.human_hints.save()
            return {"ok": True, "id": hint_id, "status": self.human_hints.status()}