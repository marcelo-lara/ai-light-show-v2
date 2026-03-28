from typing import Any, Dict, List

import httpx

from config import LLM_BASE_URL


def _chunk_text(content: str, chunk_size: int = 48) -> List[str]:
    return [content[index:index + chunk_size] for index in range(0, len(content), chunk_size)] or [""]


async def _llm_complete(client: httpx.AsyncClient, payload: Dict[str, Any]) -> Dict[str, Any]:
    response = await client.post(f"{LLM_BASE_URL}/v1/chat/completions", json=payload)
    response.raise_for_status()
    return response.json()