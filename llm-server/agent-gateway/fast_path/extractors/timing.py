import re
from typing import Any, Dict, Optional


def _find_previous_beat_time(result: Dict[str, Any], boundary_time: float) -> Optional[float]:
    if not isinstance(result, dict) or not result.get("ok"):
        return None
    previous_times = [float(beat.get("time", 0.0) or 0.0) for beat in ((result.get("data") or {}).get("beats") or []) if float(beat.get("time", 0.0) or 0.0) < float(boundary_time)]
    return max(previous_times) if previous_times else None


def _extract_time_seconds(prompt: str) -> Optional[float]:
    match = re.search(r"\b(?:at|on)\s+(?:second\s+)?(\d+(?:\.\d+)?)\s*(?:s|sec|secs|seconds?)?\b", str(prompt or ""), flags=re.IGNORECASE)
    return float(match.group(1)) if match else None


def _extract_beat_duration(prompt: str) -> Optional[float]:
    match = re.search(r"\bfor\s+(\d+(?:\.\d+)?)\s+beat(?:s)?\b", str(prompt or ""), flags=re.IGNORECASE)
    return float(match.group(1)) if match else None


def _estimate_beat_seconds(result: Dict[str, Any], cue_time: float) -> Optional[float]:
    if not isinstance(result, dict) or not result.get("ok"):
        return None
    beat_times = sorted({round(float(beat.get("time", 0.0) or 0.0), 6) for beat in ((result.get("data") or {}).get("beats") or [])})
    if len(beat_times) < 2:
        return None
    for current, nxt in zip(beat_times, beat_times[1:]):
        if current <= cue_time <= nxt:
            return max(0.0, nxt - current)
    intervals = [nxt - current for current, nxt in zip(beat_times, beat_times[1:]) if nxt > current]
    if not intervals:
        return None
    nearest_interval = min(intervals, key=lambda interval: abs(interval - min(intervals)))
    return max(0.0, nearest_interval)


def _extract_bar_beat(prompt: str) -> Optional[tuple[int, int]]:
    match = re.search(r"bar\s+(\d+)(?:[\.:](\d+))?", str(prompt or ""), flags=re.IGNORECASE)
    return (int(match.group(1)), int(match.group(2) or 1)) if match else None


def _find_first_beat_at_or_after(result: Dict[str, Any], boundary_time: float) -> Optional[float]:
    if not isinstance(result, dict) or not result.get("ok"):
        return None
    candidate_times = [float(beat.get("time", 0.0) or 0.0) for beat in ((result.get("data") or {}).get("beats") or []) if float(beat.get("time", 0.0) or 0.0) >= float(boundary_time)]
    return min(candidate_times) if candidate_times else None


def _find_next_beat_after(result: Dict[str, Any], boundary_time: float) -> Optional[float]:
    if not isinstance(result, dict) or not result.get("ok"):
        return None
    candidate_times = [float(beat.get("time", 0.0) or 0.0) for beat in ((result.get("data") or {}).get("beats") or []) if float(beat.get("time", 0.0) or 0.0) > float(boundary_time)]
    return min(candidate_times) if candidate_times else None