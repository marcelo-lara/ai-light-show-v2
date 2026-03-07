from __future__ import annotations


async def apply_16bit(manager, fixture, channel_name: str, value) -> bool:
    msb_key = f"{channel_name}_msb"
    lsb_key = f"{channel_name}_lsb"
    if msb_key not in fixture.channels or lsb_key not in fixture.channels:
        return False
    try:
        int_value = int(value)
    except Exception:
        return False
    msb, lsb = (int_value >> 8) & 0xFF, int_value & 0xFF
    applied_msb = await manager.state_manager.update_dmx_channel(int(fixture.channels[msb_key]), msb)
    applied_lsb = await manager.state_manager.update_dmx_channel(int(fixture.channels[lsb_key]), lsb)
    return bool(applied_msb or applied_lsb)


async def apply_8bit(manager, fixture, channel_key: str, value) -> bool:
    if channel_key not in fixture.channels:
        return False
    try:
        v = max(0, min(255, int(value)))
    except Exception:
        return False
    return bool(await manager.state_manager.update_dmx_channel(int(fixture.channels[channel_key]), v))


async def apply_preset(manager, fixture, preset_id: str) -> bool:
    if not hasattr(fixture, "_find_preset_values"):
        return False
    preset_values = fixture._find_preset_values(preset_id)
    if not preset_values:
        return False
    changed = False
    for key, value in preset_values.items():
        if key in ("pan", "tilt"):
            changed = (await apply_16bit(manager, fixture, key, value)) or changed
            continue
        changed = (await apply_8bit(manager, fixture, key, value)) or changed
    return changed
