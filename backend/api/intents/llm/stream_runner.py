from __future__ import annotations

import asyncio
import json

import httpx

from api.intents.llm.config import load_llm_config
from api.intents.llm.request_payload import build_chat_request
from api.intents.llm.stream_parser import parse_stream_line


async def stream_prompt(manager, prompt: str) -> None:
    config = load_llm_config()
    payload = build_chat_request(manager, prompt, config.model, config.temperature)
    timeout = httpx.Timeout(config.timeout_seconds, connect=min(config.timeout_seconds, 10.0))
    finished = False

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", f"{config.base_url}/v1/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    chunk, done = parse_stream_line(line)
                    if chunk:
                        await _broadcast_chunk(manager, chunk, False)
                    if done:
                        await _broadcast_chunk(manager, "", True)
                        finished = True
                        break
    except asyncio.CancelledError:
        raise
    except httpx.HTTPStatusError as error:
        await _broadcast_failure(manager, f"llm_http_{error.response.status_code}")
        return
    except (httpx.HTTPError, ValueError, json.JSONDecodeError) as error:
        await _broadcast_failure(manager, str(error) or "llm_request_failed")
        return

    if not finished:
        await _broadcast_chunk(manager, "", True)


async def _broadcast_chunk(manager, chunk: str, done: bool) -> None:
    await manager.broadcast_event("info", "llm_stream", {"domain": "llm", "chunk": chunk, "done": done})


async def _broadcast_failure(manager, error: str) -> None:
    await manager.broadcast_event("error", "llm_failed", {"domain": "llm", "error": error})