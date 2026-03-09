from __future__ import annotations

from typing import Any, Dict


async def _sync_state_channel(manager, absolute_channel: int, value: int) -> None:
    # Keep backend snapshot values aligned with live set_values changes.
    await manager.state_manager.update_dmx_channel(int(absolute_channel), int(value))


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
                msb_channel = fixture.absolute_channels[mc.channels[0]]
                lsb_channel = fixture.absolute_channels[mc.channels[1]]
                await manager.artnet_service.set_channel(msb_channel, msb)
                await manager.artnet_service.set_channel(lsb_channel, lsb)
                await _sync_state_channel(manager, msb_channel, msb)
                await _sync_state_channel(manager, lsb_channel, lsb)
                changed = True
            except (ValueError, TypeError):
                pass
        elif mc.kind == "enum" and mc.channel and mc.mapping:
            # Resolve label to DMX value from fixture mappings
            mapping = fixture.mappings.get(mc.mapping, {})
            # Flip the mapping to find the DMX value by label
            reverse_mapping = {v: k for k, v in mapping.items()}
            dmx_val = reverse_mapping.get(str(value))
            
            if dmx_val is not None:
                try:
                    dmx_channel = fixture.absolute_channels[mc.channel]
                    dmx_value = int(dmx_val)
                    await manager.artnet_service.set_channel(dmx_channel, dmx_value)
                    await _sync_state_channel(manager, dmx_channel, dmx_value)
                    changed = True
                except (ValueError, TypeError):
                    pass
        elif mc.channel:
            try:
                dmx_channel = fixture.absolute_channels[mc.channel]
                dmx_value = int(value)
                await manager.artnet_service.set_channel(dmx_channel, dmx_value)
                await _sync_state_channel(manager, dmx_channel, dmx_value)
                changed = True
            except (ValueError, TypeError):
                pass

    return changed
