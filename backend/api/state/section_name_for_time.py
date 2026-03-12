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
            start_raw = s.get("start_s")
            if start_raw is None:
                start_raw = s.get("start")

            end_raw = s.get("end_s")
            if end_raw is None:
                end_raw = s.get("end")

            start = float(start_raw or 0.0)
            end = float(end_raw or 0.0)
        except Exception:
            continue
            
        if start <= t <= end:
            return str(s.get("name") or s.get("label") or "")
            
    return None
