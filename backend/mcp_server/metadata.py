from __future__ import annotations

import difflib
import json
from pathlib import Path
import re

from models.song.artifacts import get_essentia_artifact_entry

from .responses import fail, ok
from .section_analysis import build_section_analysis
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


def _slice_by_bar_beat(
    rows: list[dict],
    start_bar: int | None,
    start_beat: int | None,
    end_bar: int | None,
    end_beat: int | None,
) -> list[dict]:
    if start_bar is None and start_beat is None and end_bar is None and end_beat is None:
        return rows
    start_position = (int(start_bar or 0), int(start_beat or 1))
    end_position = (int(end_bar), int(end_beat or 4)) if end_bar is not None else None
    sliced = []
    for row in rows:
        bar = row.get("bar")
        beat = row.get("beat")
        if not isinstance(bar, int) or not isinstance(beat, int):
            continue
        position = (bar, beat)
        if position < start_position:
            continue
        if end_position is not None and position > end_position:
            continue
        sliced.append(row)
    return sliced


def _find_bar_beat(rows: list[dict], bar: int, beat: int) -> dict | None:
    return next(
        (
            row
            for row in rows
            if int(row.get("bar", -1)) == int(bar) and int(row.get("beat", -1)) == int(beat)
        ),
        None,
    )


SECTION_QUERY_STOPWORDS = {
    "a",
    "an",
    "at",
    "begin",
    "begins",
    "beginning",
    "does",
    "end",
    "ends",
    "ending",
    "for",
    "is",
    "of",
    "section",
    "start",
    "starts",
    "starting",
    "the",
    "when",
    "where",
}


def _normalize_section_query(value: str) -> str:
    words = re.findall(r"[a-z0-9]+", str(value).lower())
    filtered = [word for word in words if word not in SECTION_QUERY_STOPWORDS]
    return " ".join(filtered or words)


def _find_section_match(sections: list[dict], query: str) -> dict | None:
    raw_query = str(query or "").strip().lower()
    if not raw_query:
        return None
    normalized_query = _normalize_section_query(raw_query)
    match = next((section for section in sections if raw_query == str(section.get("name") or "").strip().lower()), None)
    if match is not None:
        return match
    match = next((section for section in sections if normalized_query == _normalize_section_query(str(section.get("name") or ""))), None)
    if match is not None:
        return match
    query_words = set(normalized_query.split())
    match = next(
        (
            section
            for section in sections
            if query_words and set(_normalize_section_query(str(section.get("name") or "")).split()).issubset(query_words)
        ),
        None,
    )
    if match is not None:
        return match
    normalized_names = {_normalize_section_query(str(section.get("name") or "")): section for section in sections}
    close_matches = difflib.get_close_matches(normalized_query, list(normalized_names.keys()), n=1, cutoff=0.6)
    if close_matches:
        return normalized_names[close_matches[0]]
    return None


def register_metadata_tools(mcp, runtime) -> None:
    def _load_song(song: str | None):
        ws_manager = runtime.require_ws_manager()
        song_service = runtime.require_song_service()
        current_song = ws_manager.state_manager.current_song
        requested_song = str(song or "").strip()
        if not requested_song:
            return ws_manager, current_song, None
        if current_song is not None and requested_song == str(current_song.song_id):
            return ws_manager, current_song, None
        available_songs = song_service.list_songs()
        if requested_song not in available_songs:
            if current_song is not None:
                return ws_manager, current_song, None
            return ws_manager, None, fail("song_not_found", f"Song '{requested_song}' not found", {"songs": available_songs})
        try:
            return ws_manager, song_service.load_metadata(requested_song), None
        except FileNotFoundError as exc:
            if current_song is not None:
                return ws_manager, current_song, None
            return ws_manager, None, fail("song_metadata_unavailable", str(exc))

    @mcp.tool()
    def metadata_get_overview(song: str | None = None):
        ws_manager, current_song, error = _load_song(song)
        if error is not None:
            return error
        if current_song is None:
            return fail("song_not_loaded", "No song is currently loaded")
        details = build_song_details(current_song, ws_manager.state_manager.meta_path)
        return ok({"song": details["filename"], "length_s": details["length_s"], "bpm": details["bpm"], "sections": len(details["sections"]), "beats": len(details["beats"]), "chords": len((details.get("analysis") or {}).get("chords") or [])})

    @mcp.tool()
    def metadata_get_sections(song: str | None = None):
        ws_manager, current_song, error = _load_song(song)
        if error is not None:
            return error
        if current_song is None:
            return fail("song_not_loaded", "No song is currently loaded")
        details = build_song_details(current_song, ws_manager.state_manager.meta_path)
        return ok({"song": details["filename"], "sections": details["sections"], "count": len(details["sections"])})

    @mcp.tool()
    def metadata_get_section_analysis(song: str | None = None, section_name: str | None = None):
        ws_manager, current_song, error = _load_song(song)
        if error is not None:
            return error
        if current_song is None:
            return fail("song_not_loaded", "No song is currently loaded")
        details = build_song_details(current_song, ws_manager.state_manager.meta_path)
        sections = build_section_analysis(current_song, Path(ws_manager.state_manager.meta_path), details)
        if section_name:
            match = _find_section_match(sections, str(section_name))
            if match is None:
                return fail("section_not_found", f"Section '{section_name}' not found", {"section_name": section_name, "available_sections": [section.get("name") for section in sections]})
            return ok({"song": details["filename"], "section": match})
        return ok({"song": details["filename"], "sections": sections, "count": len(sections)})

    @mcp.tool()
    def metadata_find_section(section_name: str, song: str | None = None):
        ws_manager, current_song, error = _load_song(song)
        if error is not None:
            return error
        if current_song is None:
            return fail("song_not_loaded", "No song is currently loaded")
        query = str(section_name or "").strip().lower()
        if not query:
            return fail("section_name_required", "section_name is required")
        details = build_song_details(current_song, ws_manager.state_manager.meta_path)
        match = _find_section_match(details["sections"], query)
        if match is None:
            return fail("section_not_found", f"Section '{section_name}' not found", {"section_name": section_name, "available_sections": [section.get("name") for section in details["sections"]]})
        return ok({"song": details["filename"], "section": match})

    @mcp.tool()
    def metadata_get_beats(song: str | None = None, start_time: float | None = None, end_time: float | None = None):
        ws_manager, current_song, error = _load_song(song)
        if error is not None:
            return error
        if current_song is None:
            return fail("song_not_loaded", "No song is currently loaded")
        details = build_song_details(current_song, ws_manager.state_manager.meta_path)
        beats = _slice_by_time(details["beats"], start_time, end_time, "time")
        return ok({"song": details["filename"], "beats": beats, "count": len(beats)})

    @mcp.tool()
    def metadata_get_bar_beats(
        song: str | None = None,
        start_bar: int | None = None,
        start_beat: int | None = None,
        end_bar: int | None = None,
        end_beat: int | None = None,
    ):
        ws_manager, current_song, error = _load_song(song)
        if error is not None:
            return error
        if current_song is None:
            return fail("song_not_loaded", "No song is currently loaded")
        details = build_song_details(current_song, ws_manager.state_manager.meta_path)
        beats = _slice_by_bar_beat(details["beats"], start_bar, start_beat, end_bar, end_beat)
        return ok({"song": details["filename"], "beats": beats, "count": len(beats)})

    @mcp.tool()
    def metadata_find_bar_beat(bar: int, beat: int, song: str | None = None):
        ws_manager, current_song, error = _load_song(song)
        if error is not None:
            return error
        if current_song is None:
            return fail("song_not_loaded", "No song is currently loaded")
        details = build_song_details(current_song, ws_manager.state_manager.meta_path)
        match = _find_bar_beat(details["beats"], bar, beat)
        if match is None:
            return fail(
                "bar_beat_not_found",
                f"Bar {int(bar)} beat {int(beat)} not found",
                {"bar": int(bar), "beat": int(beat)},
            )
        return ok({"song": details["filename"], "position": match})

    @mcp.tool()
    def metadata_get_chords(
        song: str | None = None,
        start_time: float | None = None,
        end_time: float | None = None,
        start_bar: int | None = None,
        start_beat: int | None = None,
        end_bar: int | None = None,
        end_beat: int | None = None,
    ):
        ws_manager, current_song, error = _load_song(song)
        if error is not None:
            return error
        if current_song is None:
            return fail("song_not_loaded", "No song is currently loaded")
        details = build_song_details(current_song, ws_manager.state_manager.meta_path)
        chords = _slice_by_time((details.get("analysis") or {}).get("chords") or [], start_time, end_time, "time_s")
        chords = _slice_by_bar_beat(chords, start_bar, start_beat, end_bar, end_beat)
        return ok({"song": details["filename"], "chords": chords, "count": len(chords)})

    @mcp.tool()
    def metadata_find_chord(chord: str, song: str | None = None, occurrence: int = 1):
        ws_manager, current_song, error = _load_song(song)
        if error is not None:
            return error
        if current_song is None:
            return fail("song_not_loaded", "No song is currently loaded")
        requested = str(chord or "").strip().lower()
        if not requested:
            return fail("chord_required", "chord is required")
        details = build_song_details(current_song, ws_manager.state_manager.meta_path)
        matches = [entry for entry in (details.get("analysis") or {}).get("chords") or [] if str(entry.get("label") or "").strip().lower() == requested]
        index = max(0, int(occurrence or 1) - 1)
        if index >= len(matches):
            return fail(
                "chord_not_found",
                f"Chord '{chord}' occurrence {int(occurrence or 1)} not found",
                {"chord": chord, "occurrence": int(occurrence or 1), "available": len(matches)},
            )
        return ok({"song": details["filename"], "chord": matches[index], "occurrence": index + 1})

    @mcp.tool()
    def metadata_get_loudness(song: str | None = None, start_time: float | None = None, end_time: float | None = None, section: str | None = None):
        ws_manager, current_song, error = _load_song(song)
        if error is not None:
            return error
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
        loudness_entry = get_essentia_artifact_entry(getattr(current_song.meta, "artifacts", {}) or {}, "mix", "loudness_envelope")
        raw_path = str((loudness_entry or {}).get("json") or Path(ws_manager.state_manager.meta_path) / current_song.song_id / "essentia" / "loudness_envelope.json")
        if raw_path.startswith("/app/meta/"):
            path = Path(ws_manager.state_manager.meta_path) / Path(raw_path[len("/app/meta/"):])
        else:
            path = Path(raw_path)
        if not path.exists():
            return fail("loudness_unavailable", "Loudness envelope not found")
        payload = json.loads(path.read_text(encoding="utf-8"))
        times = payload.get("times") or []
        loudness = payload.get("loudness") or []
        values = [float(value) for time_value, value in zip(times, loudness) if float(time_value) >= start_value and (end_value is None or float(time_value) <= end_value)]
        if not values:
            return fail("loudness_empty", "No loudness samples in selected window")
        return ok({"song": details["filename"], "start_time": start_value, "end_time": end_value, "average": round(sum(values) / len(values), 6), "minimum": round(min(values), 6), "maximum": round(max(values), 6), "samples": len(values)})
