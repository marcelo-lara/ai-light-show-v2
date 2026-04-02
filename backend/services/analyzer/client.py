from __future__ import annotations

from typing import Any

import httpx


class AnalyzerHttpClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    @staticmethod
    def _status_timeout() -> httpx.Timeout:
        return httpx.Timeout(5.0)

    @staticmethod
    def _mutation_timeout() -> httpx.Timeout:
        return httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)

    async def get_status(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._status_timeout()) as client:
            response = await client.get(f"{self.base_url}/queue/status")
            response.raise_for_status()
            return response.json()

    async def get_task_types(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self._status_timeout()) as client:
            response = await client.get(f"{self.base_url}/task-types")
            response.raise_for_status()
            payload = response.json()
            task_types = payload.get("task_types")
            return task_types if isinstance(task_types, list) else []

    async def set_playback_lock(self, locked: bool) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._status_timeout()) as client:
            response = await client.post(f"{self.base_url}/runtime/playback-lock", json={"locked": locked})
            response.raise_for_status()
            return response.json()

    async def list_items(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self._status_timeout()) as client:
            response = await client.get(f"{self.base_url}/queue/items")
            response.raise_for_status()
            payload = response.json()
            items = payload.get("items")
            return items if isinstance(items, list) else []

    async def add_item(self, task_type: str, params: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._mutation_timeout()) as client:
            response = await client.post(
                f"{self.base_url}/queue/items",
                json={"task_type": task_type, "params": params},
            )
            response.raise_for_status()
            return response.json()

    async def enqueue_full_artifact_playlist(self, params: dict[str, Any], activate: bool = True) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._mutation_timeout()) as client:
            response = await client.post(
                f"{self.base_url}/queue/playlists/full-artifact",
                json={**params, "activate": activate},
            )
            response.raise_for_status()
            return response.json()

    async def remove_item(self, item_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._mutation_timeout()) as client:
            response = await client.delete(f"{self.base_url}/queue/items/{item_id}")
            response.raise_for_status()
            return response.json()

    async def execute_item(self, item_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._mutation_timeout()) as client:
            response = await client.post(f"{self.base_url}/queue/items/{item_id}/execute")
            response.raise_for_status()
            return response.json()