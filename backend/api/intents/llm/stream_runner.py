from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List

import httpx

from api.intents.llm.config import load_llm_config
from api.intents.llm.request_payload import build_chat_request
from api.intents.llm.stream_parser import parse_stream_line


async def stream_prompt(manager, prompt: str, history: List[Dict[str, Any]] | None = None) -> None:
    config = load_llm_config()
    payload = await build_chat_request(manager, prompt, config.model, config.temperature, history)
    timeout = httpx.Timeout(config.timeout_seconds, connect=min(config.timeout_seconds, 10.0))
    saw_content = False

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", f"{config.gateway_url}/v1/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    event = parse_stream_line(line)
                    if event is None:
                        continue

                    event_type = event["type"]
                    if event_type == "status":
                        await _broadcast_status(manager, event["status"])
                        continue

                    if event_type == "error":
                        await _broadcast_failure(manager, event["error"])
                        return

                    if event_type == "content":
                        saw_content = True
                        await _broadcast_chunk(manager, event["content"], bool(event.get("done")))
                        if event.get("done"):
                            return
                        continue

                    if event_type == "done":
                        if saw_content:
                            await _broadcast_chunk(manager, "", True)
                            return
                        break
    except asyncio.CancelledError:
        raise
    except httpx.HTTPStatusError as error:
        await _broadcast_failure(manager, f"llm_http_{error.response.status_code}")
        return
    except (httpx.HTTPError, ValueError, json.JSONDecodeError) as error:
        await _broadcast_failure(manager, str(error) or "llm_request_failed")
        return

    await _broadcast_failure(manager, "llm_empty_response")


async def _broadcast_chunk(manager, chunk: str, done: bool) -> None:
    await manager.broadcast_event("info", "llm_stream", {"domain": "llm", "chunk": chunk, "done": done})


async def _broadcast_status(manager, status: str) -> None:
    await manager.broadcast_event("info", "llm_status", {"domain": "llm", "status": status})


async def _broadcast_failure(manager, error: str) -> None:
    await manager.broadcast_event("error", "llm_failed", {"domain": "llm", "error": error})