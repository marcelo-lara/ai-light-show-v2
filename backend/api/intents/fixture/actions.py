from __future__ import annotations
from typing import Any, Dict

async def set_arm(manager, payload: Dict[str, Any]) -> bool:
    fixture_id = str(payload.get("fixture_id") or "")
    if not fixture_id:
        await manager.broadcast_event("error", "fixture_id_required")
        return False
    manager.fixture_armed[fixture_id] = bool(payload.get("armed", False))
    return True

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

    should_flush = False
    channel_types = fixture.meta.get("channel_types", {})
    
    for channel_name, value in values.items():
        ctype = channel_types.get(channel_name)
        
        # Check for preset/POI handling
        if channel_name == "preset":
            preset_id = str(value)
            if hasattr(fixture, "_find_preset_values"):
                preset_values = fixture._find_preset_values(preset_id)
                if preset_values:
                    for k, v in preset_values.items():
                        if k in ("pan", "tilt"):
                            msb_key, lsb_key = f"{k}_msb", f"{k}_lsb"
                            if msb_key in fixture.channels and lsb_key in fixture.channels:
                                iv = int(v)
                                msb, lsb = (iv >> 8) & 0xFF, iv & 0xFF
                                applied_msb = await manager.state_manager.update_dmx_channel(int(fixture.channels[msb_key]), msb)
                                applied_lsb = await manager.state_manager.update_dmx_channel(int(fixture.channels[lsb_key]), lsb)
                                should_flush = should_flush or applied_msb or applied_lsb
            continue

        # Check for position_16bit handling
        if ctype == "position_16bit":
            msb_key = f"{channel_name}_msb"
            lsb_key = f"{channel_name}_lsb"
            if msb_key in fixture.channels and lsb_key in fixture.channels:
                try:
                    v = int(value)
                    msb, lsb = (v >> 8) & 0xFF, v & 0xFF
                    applied_msb = await manager.state_manager.update_dmx_channel(int(fixture.channels[msb_key]), msb)
                    applied_lsb = await manager.state_manager.update_dmx_channel(int(fixture.channels[lsb_key]), lsb)
                    should_flush = should_flush or applied_msb or applied_lsb
                except Exception:
                    continue
        elif channel_name in fixture.channels:
            try:
                v = int(value)
                applied = await manager.state_manager.update_dmx_channel(int(fixture.channels[channel_name]), max(0, min(255, v)))
                should_flush = should_flush or applied
            except Exception:
                continue
        elif ctype and ctype in fixture.channels:
            try:
                v = int(value)
                applied = await manager.state_manager.update_dmx_channel(int(fixture.channels[ctype]), max(0, min(255, v)))
                should_flush = should_flush or applied
            except Exception:
                continue
        else:
            if channel_name in fixture.channels:
                try:
                    v = int(value)
                    applied = await manager.state_manager.update_dmx_channel(int(fixture.channels[channel_name]), max(0, min(255, v)))
                    should_flush = should_flush or applied
                except Exception:
                    continue

    if should_flush:
        universe = await manager.state_manager.get_output_universe()
        await manager.artnet_service.update_universe(universe)

    return True

async def preview_effect(manager, payload: Dict[str, Any]) -> bool:
    fixture_id = str(payload.get("fixture_id") or "")
    effect = str(payload.get("effect_id") or "")
    duration_ms = payload.get("duration_ms")
    params = payload.get("params") or {}

    try:
        duration = max(0.0, float(str(duration_ms)) / 1000.0)
    except Exception:
        duration = 0.5

    result = await manager.state_manager.start_preview_effect(
        fixture_id=fixture_id,
        effect=effect,
        duration=duration,
        data=params if isinstance(params, dict) else {},
        request_id=None,
    )

    if not result.get("ok"):
        await manager.broadcast_event("warning", "preview_rejected", result)
        return False

    universe = await manager.state_manager.get_output_universe()
    await manager.artnet_service.update_universe(universe)
    await manager.artnet_service.set_continuous_send(True)
    await manager.broadcast_event("info", "preview_started", result)
    return True

async def stop_preview(manager, payload: Dict[str, Any]) -> bool:
    await manager.broadcast_event("warning", "stop_preview_not_implemented")
    return False

# Mapping of action names to functions
FIXTURE_HANDLERS = {
    "fixture.set_arm": set_arm,
    "fixture.set_values": set_values,
    "fixture.preview_effect": preview_effect,
    "fixture.stop_preview": stop_preview,
}
