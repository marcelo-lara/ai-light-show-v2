import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx


@dataclass
class McpConnInfo:
    session_id: str
    messages_url: str  # absolute URL


class McpSseConnection:
    """
    Persistent MCP-over-SSE connection.
    Keeps /sse open, and receives JSON-RPC responses/events via SSE data.
    Sends requests via POST /messages/?session_id=...
    """

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=None)
        self._conn: Optional[McpConnInfo] = None
        self._reader_task: Optional[asyncio.Task] = None

        # Map JSON-RPC id -> Future
        self._pending: Dict[Any, asyncio.Future] = {}
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        async with self._lock:
            if self._reader_task:
                return
            self._conn = await self._open_sse_and_get_endpoint()
            self._reader_task = asyncio.create_task(self._reader_loop())

    async def close(self) -> None:
        async with self._lock:
            if self._reader_task:
                self._reader_task.cancel()
                self._reader_task = None
            await self._client.aclose()

    async def _open_sse_and_get_endpoint(self) -> McpConnInfo:
        url = f"{self.base_url}/sse"
        async with self._client.stream("GET", url, headers={"Accept": "text/event-stream"}) as r:
            r.raise_for_status()
            event = None
            async for line in r.aiter_lines():
                if line.startswith("event:"):
                    event = line.split(":", 1)[1].strip()
                elif line.startswith("data:") and event == "endpoint":
                    data = line.split(":", 1)[1].strip()
                    # data like: /messages/?session_id=...
                    m = re.search(r"session_id=([a-f0-9]+)", data)
                    if not m:
                        raise RuntimeError(f"Could not parse session_id from: {data}")
                    session_id = m.group(1)
                    # Build absolute messages url
                    messages_url = f"{self.base_url}{data}"
                    return McpConnInfo(session_id=session_id, messages_url=messages_url)

        raise RuntimeError("MCP /sse did not provide endpoint event")

    async def _reader_loop(self) -> None:
        """
        Keep SSE open and dispatch responses to pending futures.
        """
        url = f"{self.base_url}/sse"
        while True:
            try:
                async with self._client.stream("GET", url, headers={"Accept": "text/event-stream"}) as r:
                    r.raise_for_status()
                    async for line in r.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        payload_str = line.split(":", 1)[1].strip()
                        if not payload_str:
                            continue
                        # Some servers send non-JSON data events too; ignore those
                        try:
                            payload = json.loads(payload_str)
                        except Exception:
                            continue

                        # If this is a JSON-RPC response with an id, resolve the waiter
                        if isinstance(payload, dict) and "id" in payload:
                            msg_id = payload["id"]
                            fut = self._pending.pop(msg_id, None)
                            if fut and not fut.done():
                                fut.set_result(payload)

            except asyncio.CancelledError:
                raise
            except Exception:
                # reconnect after short backoff
                await asyncio.sleep(0.25)

    async def request(self, msg: Dict[str, Any], timeout: float = 10.0) -> Dict[str, Any]:
        """
        Send a JSON-RPC request and wait for matching response id.
        """
        if not self._conn or not self._reader_task:
            await self.start()

        msg_id = msg.get("id")
        if msg_id is None:
            raise ValueError("JSON-RPC message must include 'id'")

        loop = asyncio.get_event_loop()
        fut = loop.create_future()
        self._pending[msg_id] = fut

        # POST to messages endpoint
        r = await self._client.post(self._conn.messages_url, json=msg)
        # MCP server returns 202 Accepted on success
        r.raise_for_status()

        return await asyncio.wait_for(fut, timeout=timeout)