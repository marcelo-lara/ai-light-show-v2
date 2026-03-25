from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict, List

import httpx


class AssistantGatewayClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def stream(self, messages: List[Dict[str, Any]], assistant_id: str) -> AsyncIterator[Dict[str, Any]]:
        payload = {"messages": messages, "model": "local", "temperature": 0.2, "tool_choice": "auto", "stream": True, "assistant_id": assistant_id}
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{self.base_url}/v1/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    if not data:
                        continue
                    yield json.loads(data)