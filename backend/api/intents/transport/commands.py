from __future__ import annotations
from typing import Any, Dict

async def play(manager, payload: Dict[str, Any]) -> bool:
    await manager.state_manager.set_playback_state(True)
    await manager.artnet_service.set_continuous_send(True)
    return True

async def pause(manager, payload: Dict[str, Any]) -> bool:
    await manager.state_manager.set_playback_state(False)
    await manager.artnet_service.set_continuous_send(False)
    return True

async def stop(manager, payload: Dict[str, Any]) -> bool:
    await manager.state_manager.set_playback_state(False)
    await manager.state_manager.seek_timecode(0.0)
    universe = await manager.state_manager.get_output_universe()
    await manager.artnet_service.update_universe(universe)
    await manager.artnet_service.set_continuous_send(False)
    return True

async def jump_to_time(manager, payload: Dict[str, Any]) -> bool:
    raw = payload.get("time_ms")
    try:
        target = max(0.0, float(str(raw)) / 1000.0)
    except Exception:
        await manager.broadcast_event("error", "invalid_time_ms")
        return False
    await manager.state_manager.seek_timecode(target)
    universe = await manager.state_manager.get_output_universe()
    await manager.artnet_service.update_universe(universe)
    return True

async def jump_to_section(manager, payload: Dict[str, Any]) -> bool:
    await manager.broadcast_event("warning", "jump_to_section_not_implemented")
    return False

# Mapping of command names to functions
TRANSPORT_HANDLERS = {
    "transport.play": play,
    "transport.pause": pause,
    "transport.stop": stop,
    "transport.jump_to_time": jump_to_time,
    "transport.jump_to_section": jump_to_section,
}
