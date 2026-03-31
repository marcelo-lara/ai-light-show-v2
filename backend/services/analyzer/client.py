from __future__ import annotations

from typing import Any

import httpx


class AnalyzerHttpClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def get_status(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{self.base_url}/queue/status")
            response.raise_for_status()
            return response.json()

    async def set_playback_lock(self, locked: bool) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(f"{self.base_url}/runtime/playback-lock", json={"locked": locked})
            response.raise_for_status()
            return response.json()