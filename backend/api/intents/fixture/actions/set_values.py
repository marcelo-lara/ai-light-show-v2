from __future__ import annotations

from typing import Any, Dict

from models.fixtures.rgb_utils import resolve_rgb_value


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

    rgb_channel_names = set()
    for mc in fixture.meta_channels.values():
        if mc.kind == "rgb" and mc.channels:
            for channel_name in mc.channels:
                rgb_channel_names.add(str(channel_name))

    changed = False
    for key, value in values.items():
        if key in rgb_channel_names:
            # rgb fixtures accept semantic values via their rgb meta-channel only.
            continue

        if key in fixture.meta_channels:
            mc = fixture.meta_channels[key]

            # Apply to live Art-Net.
            if mc.kind == "u16" and mc.channels and len(mc.channels) == 2:
                fixture.current_values[key] = value
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
                fixture.current_values[key] = value
                # Resolve label to DMX value from fixture mappings.
                mapping = fixture.mappings.get(mc.mapping, {})
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
            elif mc.kind == "rgb" and mc.channels and len(mc.channels) >= 3:
                mapping = fixture.mappings.get(mc.mapping, {}) if mc.mapping else {}
                resolved = resolve_rgb_value(value, mapping)
                if resolved is None:
                    continue

                red, green, blue, canonical_hex = resolved
                values_by_channel = [red, green, blue]

                try:
                    for idx, channel_name in enumerate(mc.channels[:3]):
                        dmx_channel = fixture.absolute_channels[channel_name]
                        dmx_value = int(values_by_channel[idx])
                        await manager.artnet_service.set_channel(dmx_channel, dmx_value)
                        await _sync_state_channel(manager, dmx_channel, dmx_value)
                    fixture.current_values[key] = canonical_hex
                    changed = True
                except (ValueError, TypeError, KeyError):
                    pass
            elif mc.channel:
                fixture.current_values[key] = value
                try:
                    dmx_channel = fixture.absolute_channels[mc.channel]
                    dmx_value = int(value)
                    await manager.artnet_service.set_channel(dmx_channel, dmx_value)
                    await _sync_state_channel(manager, dmx_channel, dmx_value)
                    changed = True
                except (ValueError, TypeError):
                    pass
            continue

        # Also accept direct fixture channel names (e.g. red/green/blue for par cans).
        if key in fixture.absolute_channels:
            try:
                dmx_channel = fixture.absolute_channels[key]
                dmx_value = int(value)
                await manager.artnet_service.set_channel(dmx_channel, dmx_value)
                await _sync_state_channel(manager, dmx_channel, dmx_value)
                fixture.current_values[key] = dmx_value
                changed = True
            except (ValueError, TypeError):
                pass

    return changed
