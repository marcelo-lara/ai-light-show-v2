from __future__ import annotations

import asyncio
import os
from typing import Any

from .client import AnalyzerHttpClient


def _empty_snapshot() -> dict[str, Any]:
    return {"available": False, "polling": False, "playback_locked": False, "items": [], "summary": {status: 0 for status in ["queued", "pending", "running", "complete", "failed"]}}


def _has_active_work(snapshot: dict[str, Any]) -> bool:
    summary = snapshot.get("summary") or {}
    return any(int(summary.get(status, 0)) > 0 for status in ["queued", "pending", "running"])


class AnalyzerService:
    def __init__(self) -> None:
        self._client = AnalyzerHttpClient(os.getenv("ANALYZER_BASE_URL", "http://localhost:8100"))
        self._poll_interval = float(os.getenv("ANALYZER_POLL_INTERVAL", "2.0"))
        self._snapshot = _empty_snapshot()
        self._poll_task: asyncio.Task | None = None
        self._manager = None

    def snapshot(self) -> dict[str, Any]:
        return dict(self._snapshot)

    async def start(self, manager) -> None:
        self._manager = manager
        snapshot = await self.refresh()
        if _has_active_work(snapshot):
            await self.resume_polling()

    async def stop(self) -> None:
        await self.suspend_polling()

    async def notify_queue_activity(self) -> dict[str, Any]:
        snapshot = await self.refresh()
        if _has_active_work(snapshot):
            await self.resume_polling()
        return self.snapshot()

    async def list_items(self) -> list[dict[str, Any]]:
        return await self._client.list_items()

    async def enqueue_item(self, task_type: str, params: dict[str, Any]) -> dict[str, Any]:
        result = await self._client.add_item(task_type, params)
        await self.notify_queue_activity()
        return result

    async def remove_item(self, item_id: str) -> dict[str, Any]:
        result = await self._client.remove_item(item_id)
        await self.refresh()
        return result

    async def remove_all_items(self) -> dict[str, Any]:
        items = await self.list_items()
        removed_ids: list[str] = []
        for item in items:
            if item.get("status") == "running":
                continue
            item_id = str(item.get("item_id") or "").strip()
            if not item_id:
                continue
            await self._client.remove_item(item_id)
            removed_ids.append(item_id)
        await self.refresh()
        return {"item_ids": removed_ids, "count": len(removed_ids)}

    async def execute_item(self, item_id: str) -> dict[str, Any]:
        result = await self._client.execute_item(item_id)
        await self.notify_queue_activity()
        return result

    async def execute_all_queued(self) -> dict[str, Any]:
        items = await self.list_items()
        executed_ids: list[str] = []
        for item in items:
            if item.get("status") != "queued":
                continue
            item_id = str(item.get("item_id") or "").strip()
            if not item_id:
                continue
            await self._client.execute_item(item_id)
            executed_ids.append(item_id)
        if executed_ids:
            await self.notify_queue_activity()
        else:
            await self.refresh()
        return {"item_ids": executed_ids, "count": len(executed_ids)}

    async def refresh(self) -> dict[str, Any]:
        try:
            payload = await self._client.get_status()
            next_snapshot = {**payload, "available": True, "polling": self._poll_task is not None and not self._poll_task.done()}
        except Exception as exc:
            next_snapshot = {**_empty_snapshot(), "error": str(exc)}
        changed = next_snapshot != self._snapshot
        self._snapshot = next_snapshot
        if changed and self._manager is not None and self._manager.active_connections:
            await self._manager._schedule_broadcast()
        return self.snapshot()

    async def suspend_polling(self) -> None:
        task = self._poll_task
        self._poll_task = None
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._snapshot["polling"] = False

    async def resume_polling(self) -> None:
        if self._poll_task is not None and not self._poll_task.done():
            return
        if self._manager is not None and await self._manager.state_manager.get_is_playing():
            return
        if not _has_active_work(self._snapshot):
            self._snapshot["polling"] = False
            return
        self._poll_task = asyncio.create_task(self._poll_loop())
        self._snapshot["polling"] = True

    async def lock_for_playback(self) -> tuple[bool, dict[str, Any]]:
        status = await self.refresh()
        if int((status.get("summary") or {}).get("running", 0)) > 0:
            return False, status
        if status.get("available"):
            self._snapshot = {**(await self._client.set_playback_lock(True)), "available": True, "polling": False}
        await self.suspend_polling()
        return True, self.snapshot()

    async def unlock_after_playback(self) -> None:
        if self._snapshot.get("available"):
            try:
                self._snapshot = {**(await self._client.set_playback_lock(False)), "available": True, "polling": False}
            except Exception as exc:
                self._snapshot = {**_empty_snapshot(), "error": str(exc)}
        if _has_active_work(self._snapshot):
            await self.resume_polling()
        if self._manager is not None and self._manager.active_connections:
            await self._manager._schedule_broadcast()

    async def _poll_loop(self) -> None:
        while True:
            snapshot = await self.refresh()
            if not _has_active_work(snapshot):
                self._poll_task = None
                self._snapshot["polling"] = False
                return
            await asyncio.sleep(self._poll_interval)