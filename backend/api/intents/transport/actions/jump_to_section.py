from __future__ import annotations

from typing import Any, Dict


async def jump_to_section(manager, payload: Dict[str, Any]) -> bool:
    await manager.broadcast_event("warning", "jump_to_section_not_implemented")
    return False
