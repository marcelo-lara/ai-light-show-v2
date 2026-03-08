from __future__ import annotations

from typing import Any, Dict


async def set_values(manager, payload: Dict[str, Any]) -> bool:
    fixture_id = str(payload.get("fixture_id") or "")
    values = payload.get("values") or {}
    if not fixture_id or not isinstance(values, dict):
        return False

    fixture = next((f for f in manager.state_manager.fixtures if f.id == fixture_id), None)
    if not fixture:
        return False

    changed = False
    for mc_id, value in values.items():
        if mc_id not in fixture.meta_channels:
            continue
            
        mc = fixture.meta_channels[mc_id]
        # Update current_values for snapshot persistence
        fixture.current_values[mc_id] = value
        
        # Apply to live Art-Net
        if mc.kind == "u16" and mc.channels and len(mc.channels) == 2:
            try:
                val = int(value)
                msb = (val >> 8) & 0xFF
                lsb = val & 0xFF
                await manager.artnet_service.set_channel(fixture.absolute_channels[mc.channels[0]], msb)
                await manager.artnet_service.set_channel(fixture.absolute_channels[mc.channels[1]], lsb)
                changed = True
            except (ValueError, TypeError):
                pass
        elif mc.kind == "enum" and mc.channel and mc.mapping:
            # Resolve label to DMX value from fixture mappings
            mapping = fixture.mappings.get(mc.mapping, {})
            dmx_val = mapping.get(str(value))
            if dmx_val is not None:
                try:
                    await manager.artnet_service.set_channel(fixture.absolute_channels[mc.channel], int(dmx_val))
                    changed = True
                except (ValueError, TypeError):
                    pass
        elif mc.channel:
            try:
                await manager.artnet_service.set_channel(fixture.absolute_channels[mc.channel], int(value))
                changed = True
            except (ValueError, TypeError):
                pass

    return changed
