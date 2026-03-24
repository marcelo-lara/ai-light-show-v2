from __future__ import annotations

import json
import os
from typing import Any, AsyncIterator

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse


LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://llm-server:8080")
REQUEST_TIMEOUT_SECONDS = 120.0

app = FastAPI(title="Agent Gateway")


@app.get("/health")
async def gateway_health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/chat/completions")
async def proxy_chat_completions(request: Request):
    payload = await request.json()
    timeout = httpx.Timeout(REQUEST_TIMEOUT_SECONDS, connect=min(REQUEST_TIMEOUT_SECONDS, 10.0))

    if bool(payload.get("stream")):
        return StreamingResponse(_stream_completion(payload, timeout), media_type="text/event-stream")

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(f"{LLM_BASE_URL}/v1/chat/completions", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise HTTPException(error.response.status_code, error.response.text) from error
        except httpx.HTTPError as error:
            raise HTTPException(502, str(error) or "llm_request_failed") from error
    return JSONResponse(response.json())


async def _stream_completion(payload: dict[str, Any], timeout: httpx.Timeout) -> AsyncIterator[bytes]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            async with client.stream("POST", f"{LLM_BASE_URL}/v1/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    if chunk:
                        yield chunk
        except httpx.HTTPStatusError as error:
            detail = error.response.text.replace("\n", " ").strip() or "llm_stream_failed"
            event = json.dumps({"type": "error", "error": detail})
            yield f"data: {event}\n\n".encode("utf-8")
            yield b"data: [DONE]\n\n"
        except httpx.HTTPError as error:
            detail = str(error).replace("\n", " ").strip() or "llm_stream_failed"
            event = json.dumps({"type": "error", "error": detail})
            yield f"data: {event}\n\n".encode("utf-8")
            yield b"data: [DONE]\n\n"
