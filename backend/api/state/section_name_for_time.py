from __future__ import annotations

from typing import Optional


def section_name_for_time(manager, timecode: float) -> Optional[str]:
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
