from __future__ import annotations

from typing import Any, Dict

from api.intents.cue.mutate_sheet import execute_clear_cue


async def clear_cue(manager, payload: Dict[str, Any]) -> bool:
    """Clear cue entries by time range.

    Payload:
        from_time: float (optional, defaults to 0.0)
        to_time: float (optional)
    """
    result = await execute_clear_cue(manager, payload)
    await manager.broadcast_event(result["level"], result["message"], result["data"])
    return result["ok"]
