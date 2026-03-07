from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

async def build_frontend_state(manager) -> Dict[str, Any]:
    """Assembles the full system state for frontend consumption."""
    status = await manager.state_manager.get_status()
    timecode = await manager.state_manager.get_timecode()
    universe = await manager.state_manager.get_output_universe()

    is_playing = bool(status.get("isPlaying", False))
    playback_state = "playing" if is_playing else ("stopped" if timecode <= 0.001 else "paused")
    show_state = "running" if is_playing else "idle"

    section_name = section_name_for_time(manager, timecode)
    bpm = None
    if manager.state_manager.current_song and manager.state_manager.current_song.metadata:
        bpm = manager.state_manager.current_song.metadata.bpm

    fixtures = {}
    for fixture in manager.state_manager.fixtures:
        logical_values = {}
        channel_types = fixture.meta.get("channel_types", {})
        
        ftype = str(fixture.type or "").lower()
        capabilities: Dict[str, Any] = {}
        if "moving" in ftype and "head" in ftype:
            capabilities["pan_tilt"] = True
        
        for channel_name, channel_type in channel_types.items():
            if channel_type == "position_16bit":
                msb_key = f"{channel_name}_msb"
                lsb_key = f"{channel_name}_lsb"
                if msb_key in fixture.channels and lsb_key in fixture.channels:
                    msb_idx = int(fixture.channels[msb_key]) - 1
                    lsb_idx = int(fixture.channels[lsb_key]) - 1
                    if 0 <= msb_idx < len(universe) and 0 <= lsb_idx < len(universe):
                        val = (int(universe[msb_idx]) << 8) | int(universe[lsb_idx])
                        logical_values[channel_name] = val
            else:
                target_channel_name = channel_type
                if target_channel_name in fixture.channels:
                    idx = int(fixture.channels[target_channel_name]) - 1
                    if 0 <= idx < len(universe):
                        logical_values[channel_name] = int(universe[idx])

        if "rgb" in ftype or {"red", "green", "blue"}.issubset(set((fixture.channels or {}).keys())):
            capabilities["rgb"] = True

        fixtures[fixture.id] = {
            "id": fixture.id,
            "name": fixture.name,
            "type": fixture.type,
            "armed": bool(manager.fixture_armed.get(fixture.id, True)),
            "values": logical_values,
            "capabilities": capabilities,
        }

    song_payload = build_song_payload(manager)

    return {
        "system": {
            "show_state": show_state,
            "edit_lock": is_playing,
        },
        "playback": {
            "state": playback_state,
            "time_ms": int(round(timecode * 1000.0)),
            "bpm": bpm,
            "section_name": section_name,
        },
        "fixtures": fixtures,
        "song": song_payload,
        "pois": await manager.state_manager.get_pois(),
    }

def build_song_payload(manager) -> Optional[Dict[str, Any]]:
    """Serializes the current song and its metadata."""
    song = manager.state_manager.current_song
    if not song:
        return None

    metadata = getattr(song, "metadata", None)
    hints = getattr(metadata, "hints", {}) or {}
    drums = getattr(metadata, "drums", {}) or {}
    parts = getattr(metadata, "parts", {}) or {}

    sections: List[Dict[str, Any]] = []
    for name, rng in parts.items():
        if not isinstance(rng, list) or len(rng) < 2:
            continue
        try:
            start = float(rng[0])
            end = float(rng[1])
        except Exception:
            continue
        sections.append({
            "name": str(name),
            "start_s": start,
            "end_s": end,
        })

    sections.sort(key=lambda item: float(item.get("start_s", 0.0)))

    def _pick_numeric_list(*candidates: Any) -> List[float]:
        for candidate in candidates:
            if not isinstance(candidate, list):
                continue
            picked: List[float] = []
            for value in candidate:
                try:
                    picked.append(float(value))
                except Exception:
                    continue
            if picked:
                return picked
        return []

    beats = _pick_numeric_list(hints.get("beats"), drums.get("beats"))
    downbeats = _pick_numeric_list(hints.get("downbeats"), drums.get("downbeats"))

    return {
        "filename": str(getattr(song, "filename", "") or ""),
        "audio_url": getattr(song, "audioUrl", None),
        "length_s": getattr(metadata, "length", None),
        "bpm": getattr(metadata, "bpm", None),
        "sections": sections,
        "beats": beats,
        "downbeats": downbeats,
    }

def section_name_for_time(manager, timecode: float) -> Optional[str]:
    """Finds the section name for a given timecode."""
    song = manager.state_manager.current_song
    if not song or not song.metadata or not song.metadata.parts:
        return None

    t = float(timecode)
    for name, rng in song.metadata.parts.items():
        if isinstance(rng, list) and len(rng) >= 2:
            try:
                start = float(rng[0])
                end = float(rng[1])
            except Exception:
                continue
            if start <= t <= end:
                return str(name)
    return None
