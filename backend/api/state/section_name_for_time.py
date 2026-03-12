from __future__ import annotations

from typing import Optional


def section_name_for_time(manager, timecode: float) -> Optional[str]:
    song = manager.state_manager.current_song
    if not song:
        return None

    sections = song.sections
    if not sections or not sections.sections:
        return None

    t = float(timecode)
    for s in sections.sections:
        try:
            start = float(s.get("start_s", 0.0))
            end = float(s.get("end_s", 0.0))
        except Exception:
            continue
            
        if start <= t <= end:
            return str(s.get("name", ""))
            
    return None
