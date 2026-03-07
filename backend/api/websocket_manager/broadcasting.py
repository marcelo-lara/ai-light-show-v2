from __future__ import annotations

from typing import Any, Dict
import asyncio
import json
import logging
import time

from api.state.build_frontend_state import build_frontend_state

logger = logging.getLogger(__name__)


async def schedule_broadcast(manager, now: float) -> None:
    elapsed_ms = (now - manager._last_broadcast_time) * 1000.0
    if manager._pending_broadcast_task and not manager._pending_broadcast_task.done():
        return
    if elapsed_ms >= manager._broadcast_throttle_ms:
        await execute_broadcast(manager, now)
        return
    delay = (manager._broadcast_throttle_ms - elapsed_ms) / 1000.0
    manager._pending_broadcast_task = asyncio.create_task(delayed_broadcast(manager, delay))


async def delayed_broadcast(manager, delay: float) -> None:
    await asyncio.sleep(delay)
    await execute_broadcast(manager, now=time.time())


async def execute_broadcast(manager, now: float) -> None:
    if not manager.active_connections:
        return

    new_state = await build_frontend_state(manager)
    if manager._last_state_snapshot:
        await broadcast_patch(manager, manager._last_state_snapshot, new_state)
    else:
        logger.warning("[WS] No previous snapshot to patch against, sending full snapshot")
        await manager.broadcast({"type": "snapshot", "seq": manager._next_seq(), "state": new_state})

    manager._last_state_snapshot = new_state
    manager._last_broadcast_time = now


async def broadcast_patch(manager, before: Dict[str, Any], after: Dict[str, Any]) -> None:
    changes = []
    keys = sorted(set(before.keys()) | set(after.keys()))
    for key in keys:
        if before.get(key) != after.get(key):
            changes.append({"path": [key], "value": after.get(key)})

    if not changes:
        return

    seq = manager._next_seq()
    logger.info("[WS] Broadcasting patch (seq=%s) with %s changes", seq, len(changes))
    for change in changes:
        if change["path"] == ["fixtures"]:
            logger.debug("[WS] Fixtures changed: %s", json.dumps(change["value"], indent=2))

    await manager.broadcast({"type": "patch", "seq": seq, "changes": changes})
