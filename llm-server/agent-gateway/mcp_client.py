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
    Proper MCP-over-SSE connection:
    - Keeps ONE /sse stream open (the session stream).
    - Parses 'event:endpoint' to discover messages URL + session_id.
    - Reads JSON-RPC responses from SSE 'data:' lines.
    - Sends JSON-RPC requests via POST to messages_url.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=None)

        self._conn: Optional[McpConnInfo] = None
        self._reader_task: Optional[asyncio.Task] = None

        self._ready = asyncio.Event()  # set when endpoint/session is known
        self._pending: Dict[Any, asyncio.Future] = {}

        self._lock = asyncio.Lock()

    async def start(self) -> None:
        async with self._lock:
            if self._reader_task:
                return
            self._reader_task = asyncio.create_task(self._run())
        # wait until we have session_id/messages_url
        await asyncio.wait_for(self._ready.wait(), timeout=15)

    async def close(self) -> None:
        async with self._lock:
            if self._reader_task:
                self._reader_task.cancel()
                self._reader_task = None
        # fail any pending futures
        for fut in list(self._pending.values()):
            if not fut.done():
                fut.set_exception(RuntimeError("MCP connection closed"))
        self._pending.clear()
        await self._client.aclose()

    async def _run(self) -> None:
        """
        Keep the SSE stream open forever; reconnect if it drops.
        IMPORTANT: session_id is tied to this SSE stream.
        """
        while True:
            try:
                self._ready.clear()
                self._conn = None

                url = f"{self.base_url}/sse"
                async with self._client.stream(
                    "GET", url, headers={"Accept": "text/event-stream"}
                ) as r:
                    r.raise_for_status()

                    event_name: Optional[str] = None

                    async for line in r.aiter_lines():
                        if line.startswith("event:"):
                            event_name = line.split(":", 1)[1].strip()
                            continue

                        if not line.startswith("data:"):
                            continue

                        data = line.split(":", 1)[1].strip()
                        if not data:
                            continue

                        # 1) Endpoint event gives us session + messages URL
                        if event_name == "endpoint":
                            # data like: /messages/?session_id=...
                            m = re.search(r"session_id=([a-f0-9]+)", data)
                            if not m:
                                continue
                            session_id = m.group(1)
                            messages_url = f"{self.base_url}{data}"

                            self._conn = McpConnInfo(session_id=session_id, messages_url=messages_url)
                            self._ready.set()
                            continue

                        # 2) JSON-RPC responses/events often come as JSON in data lines
                        try:
                            payload = json.loads(data)
                        except Exception:
                            continue

                        if isinstance(payload, dict) and "id" in payload:
                            msg_id = payload["id"]
                            fut = self._pending.pop(msg_id, None)
                            if fut and not fut.done():
                                fut.set_result(payload)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                # If connection drops, fail pending requests so callers don't hang forever
                for fut in list(self._pending.values()):
                    if not fut.done():
                        fut.set_exception(RuntimeError(f"MCP SSE reconnect: {e}"))
                self._pending.clear()
                await asyncio.sleep(0.25)

    async def request(self, msg: Dict[str, Any], timeout: float = 10.0) -> Dict[str, Any]:
        """
        Send a JSON-RPC message and wait for response with matching id.
        """
        if "id" not in msg:
            raise ValueError("JSON-RPC message must include an 'id'")

        # Ensure SSE session is ready
        if not self._ready.is_set():
            await self.start()

        assert self._conn is not None

        msg_id = msg["id"]
        loop = asyncio.get_event_loop()
        fut = loop.create_future()
        self._pending[msg_id] = fut

        # POST to the SAME session's messages URL
        r = await self._client.post(self._conn.messages_url, json=msg)
        r.raise_for_status()  # MCP typically returns 202 Accepted

        return await asyncio.wait_for(fut, timeout=timeout)