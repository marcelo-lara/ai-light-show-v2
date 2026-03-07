from __future__ import annotations

from typing import Any, Dict


async def cancel(manager, payload: Dict[str, Any]) -> bool:
    await manager.broadcast_event("info", "llm_cancelled", {"domain": "llm"})
    return False
