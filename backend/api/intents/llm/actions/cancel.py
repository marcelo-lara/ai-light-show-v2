from __future__ import annotations

from typing import Any, Dict


async def cancel(manager, payload: Dict[str, Any]) -> bool:
    cancelled = await manager.cancel_llm_task()
    if cancelled:
        await manager.broadcast_event("info", "llm_cancelled", {"domain": "llm"})
        return False

    await manager.broadcast_event("warning", "llm_cancel_ignored", {"domain": "llm", "reason": "not_active"})
    return False
