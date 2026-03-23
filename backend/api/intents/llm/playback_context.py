from __future__ import annotations

from typing import Any, Dict

from api.state.section_name_for_time import section_name_for_time


async def build_playback_position_payload(manager) -> Dict[str, Any]:
    time_s = await manager.state_manager.get_timecode()
    is_playing = await manager.state_manager.get_is_playing()
    section_name = section_name_for_time(manager, time_s)
    section_text = str(section_name or "")
    if section_text:
        answer = f"The cursor is at {float(time_s):g} seconds in the {section_text} section."
    else:
        answer = f"The cursor is at {float(time_s):g} seconds."
    return {
        "time_s": float(time_s),
        "time_ms": int(round(float(time_s) * 1000.0)),
        "section_name": section_text,
        "playback_state": "playing" if is_playing else ("stopped" if time_s <= 0.001 else "paused"),
        "answer": answer,
    }


async def build_playback_position_context(manager) -> str:
    payload = await build_playback_position_payload(manager)
    section_text = payload["section_name"] or "unavailable"
    return "\n".join(
        [
            "Current playback context:",
            f"- Current song position: {payload['time_s']:g} seconds",
            f"- Current section: {section_text}",
            f"- Playback state: {payload['playback_state']}",
        ]
    )