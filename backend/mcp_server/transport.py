from __future__ import annotations

from .responses import fail, ok


def _section_bounds(current_song) -> list[dict]:
    sections = []
    for section in getattr(getattr(current_song, "sections", None), "sections", []) or []:
        sections.append(
            {
                "name": str(section.get("name") or section.get("label") or "").strip(),
                "start_s": float(section.get("start_s", section.get("start", 0.0)) or 0.0),
                "end_s": float(section.get("end_s", section.get("end", 0.0)) or 0.0),
            }
        )
    return sections


def register_transport_tools(mcp, runtime) -> None:
    @mcp.tool()
    async def transport_get_cursor():
        ws_manager = runtime.require_ws_manager()
        current_song = ws_manager.state_manager.current_song
        if current_song is None:
            return fail("song_not_loaded", "No song is currently loaded")
        timecode = await ws_manager.state_manager.get_timecode()
        beats = list(getattr(getattr(current_song, "beats", None), "beats", []) or [])
        nearest = None
        for beat in beats:
            if float(beat.time) <= float(timecode):
                nearest = beat
            else:
                break
        next_beat = None
        for beat in beats:
            if float(beat.time) > float(timecode):
                next_beat = beat
                break
        section_name = None
        next_section_name = None
        for section in _section_bounds(current_song):
            if section["start_s"] <= float(timecode) <= section["end_s"]:
                section_name = section["name"]
                break
            if float(timecode) < section["start_s"] and next_section_name is None:
                next_section_name = section["name"]
        return ok(
            {
                "time_s": round(float(timecode), 3),
                "bar": getattr(nearest, "bar", None),
                "beat": getattr(nearest, "beat", None),
                "beat_time_s": round(float(getattr(nearest, "time", timecode) or timecode), 3) if nearest is not None else None,
                "next_bar": getattr(next_beat, "bar", None),
                "next_beat": getattr(next_beat, "beat", None),
                "next_beat_time_s": round(float(getattr(next_beat, "time", 0.0)), 3) if next_beat is not None else None,
                "section_name": section_name,
                "next_section_name": next_section_name,
            }
        )