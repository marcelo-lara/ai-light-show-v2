from __future__ import annotations

import json
from pathlib import Path

from .responses import fail, ok
from .song_data import build_song_details


def _slice_by_time(rows: list[dict], start_time: float | None, end_time: float | None, key: str) -> list[dict]:
    if start_time is None and end_time is None:
        return rows
    start_value = float(start_time or 0.0)
    end_value = float(end_time) if end_time is not None else None
    sliced = []
    for row in rows:
        time_value = float(row.get(key, 0.0))
        if time_value < start_value:
            continue
        if end_value is not None and time_value > end_value:
            continue
        sliced.append(row)
    return sliced


def register_metadata_tools(mcp, runtime) -> None:
    def _load_song(song: str | None):
        ws_manager = runtime.require_ws_manager()
        song_service = runtime.require_song_service()
        current_song = ws_manager.state_manager.current_song
        if song:
            current_song = song_service.load_metadata(song)
        return ws_manager, current_song

    @mcp.tool()
    def metadata_get_overview(song: str | None = None):
        ws_manager, current_song = _load_song(song)
        if current_song is None:
            return fail("song_not_loaded", "No song is currently loaded")
        details = build_song_details(current_song, ws_manager.state_manager.meta_path)
        return ok({"song": details["filename"], "length_s": details["length_s"], "bpm": details["bpm"], "sections": len(details["sections"]), "beats": len(details["beats"]), "chords": len((details.get("analysis") or {}).get("chords") or [])})

    @mcp.tool()
    def metadata_get_sections(song: str | None = None):
        ws_manager, current_song = _load_song(song)
        if current_song is None:
            return fail("song_not_loaded", "No song is currently loaded")
        details = build_song_details(current_song, ws_manager.state_manager.meta_path)
        return ok({"song": details["filename"], "sections": details["sections"], "count": len(details["sections"])})

    @mcp.tool()
    def metadata_get_beats(song: str | None = None, start_time: float | None = None, end_time: float | None = None):
        ws_manager, current_song = _load_song(song)
        if current_song is None:
            return fail("song_not_loaded", "No song is currently loaded")
        details = build_song_details(current_song, ws_manager.state_manager.meta_path)
        beats = _slice_by_time(details["beats"], start_time, end_time, "time")
        return ok({"song": details["filename"], "beats": beats, "count": len(beats)})

    @mcp.tool()
    def metadata_get_chords(song: str | None = None, start_time: float | None = None, end_time: float | None = None):
        ws_manager, current_song = _load_song(song)
        if current_song is None:
            return fail("song_not_loaded", "No song is currently loaded")
        details = build_song_details(current_song, ws_manager.state_manager.meta_path)
        chords = _slice_by_time((details.get("analysis") or {}).get("chords") or [], start_time, end_time, "time_s")
        return ok({"song": details["filename"], "chords": chords, "count": len(chords)})

    @mcp.tool()
    def metadata_get_loudness(song: str | None = None, start_time: float | None = None, end_time: float | None = None, section: str | None = None):
        ws_manager, current_song = _load_song(song)
        if current_song is None:
            return fail("song_not_loaded", "No song is currently loaded")
        details = build_song_details(current_song, ws_manager.state_manager.meta_path)
        start_value = float(start_time or 0.0)
        end_value = float(end_time) if end_time is not None else None
        if section:
            match = next((item for item in details["sections"] if str(item.get("name") or "").lower() == str(section).lower()), None)
            if match is None:
                return fail("section_not_found", f"Section '{section}' not found")
            start_value = float(match.get("start_s", 0.0))
            end_value = float(match.get("end_s", 0.0))
        path = Path(ws_manager.state_manager.meta_path) / current_song.song_id / "essentia" / "loudness_envelope.json"
        if not path.exists():
            return fail("loudness_unavailable", "Loudness envelope not found")
        payload = json.loads(path.read_text(encoding="utf-8"))
        times = payload.get("times") or []
        loudness = payload.get("loudness") or []
        values = [float(value) for time_value, value in zip(times, loudness) if float(time_value) >= start_value and (end_value is None or float(time_value) <= end_value)]
        if not values:
            return fail("loudness_empty", "No loudness samples in selected window")
        return ok({"song": details["filename"], "start_time": start_value, "end_time": end_value, "average": round(sum(values) / len(values), 6), "minimum": round(min(values), 6), "maximum": round(max(values), 6), "samples": len(values)})