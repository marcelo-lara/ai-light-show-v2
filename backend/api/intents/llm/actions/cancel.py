from __future__ import annotations

from typing import Any, Dict


async def cancel(manager, payload: Dict[str, Any]) -> bool:
    if manager.assistant_service is None:
        await manager.broadcast_event("error", "llm_error", {"domain": "llm", "code": "assistant_unavailable", "detail": "Assistant service is unavailable.", "retryable": True})
        return False
    await manager.assistant_service.cancel(manager, payload)
    return False
