from __future__ import annotations

from typing import Any, Dict


async def jump_to_section(manager, payload: Dict[str, Any]) -> bool:
    song = manager.state_manager.current_song
    if not song:
        await manager.broadcast_event("error", "song_not_loaded")
        return False

    sections = getattr(song, "sections", None)
    raw_sections = list(getattr(sections, "sections", []) or [])
    normalized = []
    for entry in raw_sections:
        if not isinstance(entry, dict):
            continue
        try:
            start_raw = entry.get("start_s")
            if start_raw is None:
                start_raw = entry.get("start")
            start_s = float(start_raw or 0.0)
        except Exception:
            continue
        normalized.append(
            {
                "start_s": max(0.0, start_s),
                "name": str(entry.get("name") or entry.get("label") or ""),
            }
        )

    if not normalized:
        await manager.broadcast_event("error", "no_sections_available")
        return False

    normalized.sort(key=lambda item: item["start_s"])

    raw_index = payload.get("section_index")
    try:
        section_index = int(str(raw_index))
    except Exception:
        await manager.broadcast_event("error", "invalid_section_index")
        return False

    if section_index < 0 or section_index >= len(normalized):
        await manager.broadcast_event(
            "error",
            "section_index_out_of_range",
            {"section_index": section_index, "section_count": len(normalized)},
        )
        return False

    await manager.state_manager.seek_timecode(normalized[section_index]["start_s"])
    universe = await manager.state_manager.get_output_universe()
    await manager.artnet_service.update_universe(universe)
    return True
