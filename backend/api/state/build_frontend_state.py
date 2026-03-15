from __future__ import annotations

from typing import Any, Dict

from api.state.cue_helpers import build_cue_helpers_payload
from api.state.fixtures import build_fixtures_payload
from api.state.section_name_for_time import section_name_for_time
from api.state.song_payload import build_song_payload


async def build_frontend_state(manager) -> Dict[str, Any]:
    status = await manager.state_manager.get_status()
    timecode = await manager.state_manager.get_timecode()
    universe = await manager.state_manager.get_output_universe()

    is_playing = bool(status.get("isPlaying", False))
    playback_state = "playing" if is_playing else ("stopped" if timecode <= 0.001 else "paused")
    show_state = "running" if is_playing else "idle"
    bpm = getattr(getattr(manager.state_manager.current_song, "meta", None), "bpm", None)

    return {
        "system": {"show_state": show_state, "edit_lock": is_playing},
        "playback": {
            "state": playback_state,
            "time_ms": int(round(timecode * 1000.0)),
            "bpm": bpm,
            "section_name": section_name_for_time(manager, timecode),
        },
        "fixtures": build_fixtures_payload(manager, universe),
        "song": build_song_payload(manager),
        "pois": await manager.state_manager.get_pois(),
        "cues": manager.state_manager.get_cue_entries(),
        "cue_helpers": build_cue_helpers_payload(),
    }
