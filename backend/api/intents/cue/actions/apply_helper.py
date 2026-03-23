from __future__ import annotations

from typing import Any, Dict

from api.intents.cue.mutate_sheet import execute_apply_helper


async def apply_helper(manager, payload: Dict[str, Any]) -> bool:
    """Apply a cue helper to generate cue entries.

    Payload:
        helper_id: str - ID of the helper to apply
    """
    result = await execute_apply_helper(manager, payload)
    await manager.broadcast_event(result["level"], result["message"], result["data"])
    return result["ok"]