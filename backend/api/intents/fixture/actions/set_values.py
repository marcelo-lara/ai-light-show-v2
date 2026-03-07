from __future__ import annotations

from typing import Any, Dict

from api.intents.fixture.actions._set_values_helpers import apply_16bit, apply_8bit, apply_preset


async def set_values(manager, payload: Dict[str, Any]) -> bool:
    fixture_id = str(payload.get("fixture_id") or "")
    values = payload.get("values") or {}
    if not fixture_id or not isinstance(values, dict):
        await manager.broadcast_event("error", "invalid_fixture_values_payload")
        return False

    fixture = next((f for f in manager.state_manager.fixtures if f.id == fixture_id), None)
    if not fixture:
        await manager.broadcast_event("error", "fixture_not_found", {"fixture_id": fixture_id})
        return False

    changed = False
    channel_types = fixture.meta.get("channel_types", {})
    for channel_name, value in values.items():
        ctype = channel_types.get(channel_name)
        if channel_name == "preset":
            changed = (await apply_preset(manager, fixture, str(value))) or changed
            continue
        if ctype == "position_16bit":
            changed = (await apply_16bit(manager, fixture, channel_name, value)) or changed
            continue
        if channel_name in fixture.channels:
            changed = (await apply_8bit(manager, fixture, channel_name, value)) or changed
            continue
        if ctype and ctype in fixture.channels:
            changed = (await apply_8bit(manager, fixture, ctype, value)) or changed

    if changed:
        universe = await manager.state_manager.get_output_universe()
        await manager.artnet_service.update_universe(universe)
    return True
