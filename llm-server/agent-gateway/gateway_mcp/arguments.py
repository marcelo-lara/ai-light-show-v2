from typing import Any, Dict, List

from fastapi import HTTPException


def _require_song_arg(tool_name: str, args: Dict[str, Any]) -> str:
    song = args.get("song") or args.get("song_id")
    if not song:
        raise HTTPException(400, f"{tool_name} requires 'song' or 'song_id'")
    return str(song)


def _expand_subdivision_times(beat_times: List[float], subdivision: float) -> List[float]:
    if not beat_times:
        return []
    if subdivision >= 1.0:
        stride = max(1, int(round(subdivision)))
        return beat_times[::stride]
    steps = max(1, int(round(1.0 / subdivision)))
    expanded: List[float] = []
    for index in range(len(beat_times) - 1):
        start_time = beat_times[index]
        end_time = beat_times[index + 1]
        for offset in range(steps):
            expanded.append(start_time + ((end_time - start_time) * (offset / steps)))
    expanded.append(beat_times[-1])
    return [round(value, 6) for value in expanded]