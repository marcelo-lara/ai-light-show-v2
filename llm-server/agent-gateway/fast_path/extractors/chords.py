import re
from typing import Any, Dict, List, Optional


def _extract_chord_label(prompt: str) -> Optional[str]:
    match = re.search(r"chord(?:s|\s+is|s\s+is|s\s+turns\s+to|\s+turns\s+to)?\s+(none|N|[A-G](?:#|b)?m?)(?=$|\s|[^A-Za-z0-9_])", str(prompt or ""), flags=re.IGNORECASE)
    return match.group(1) if match else None


def _extract_chord_transition(prompt: str) -> Optional[tuple[str, str]]:
    match = re.search(r"changes?\s+from\s+([A-G](?:#|b)?m?)(?=\s+to\s+)\s+to\s+([A-G](?:#|b)?m?)(?=$|\s|[^A-Za-z0-9_])", str(prompt or ""), flags=re.IGNORECASE)
    return (match.group(1), match.group(2)) if match else None


def _normalize_chord_label(label: str) -> str:
    lowered = str(label or "").strip().lower()
    if lowered in {"n", "none", "no chord", "no_chord"}:
        return "n"
    return lowered


def _find_chord_transition_time(result: Dict[str, Any], start_label: str, end_label: str) -> Optional[float]:
    if not isinstance(result, dict) or not result.get("ok"):
        return None
    start_normalized = _normalize_chord_label(start_label)
    end_normalized = _normalize_chord_label(end_label)
    chords = (result.get("data") or {}).get("chords") or []
    for current, nxt in zip(chords, chords[1:]):
        if _normalize_chord_label(str(current.get("label") or current.get("chord") or "")) == start_normalized and _normalize_chord_label(str(nxt.get("label") or nxt.get("chord") or "")) == end_normalized:
            return float(nxt.get("time_s", nxt.get("time", 0.0)) or 0.0)
    return None


def _find_chord_times(result: Dict[str, Any], chord_label: str) -> List[float]:
    if not isinstance(result, dict) or not result.get("ok"):
        return []
    label_normalized = _normalize_chord_label(chord_label)
    return [float(chord.get("time_s", chord.get("time", 0.0)) or 0.0) for chord in ((result.get("data") or {}).get("chords") or []) if _normalize_chord_label(str(chord.get("label") or chord.get("chord") or "")) == label_normalized]


def _find_chord_spans(result: Dict[str, Any], chord_label: str) -> List[tuple[float, float]]:
    if not isinstance(result, dict) or not result.get("ok"):
        return []
    chords = (result.get("data") or {}).get("chords") or []
    label_normalized = _normalize_chord_label(chord_label)
    spans: List[tuple[float, float]] = []
    index = 0
    while index < len(chords):
        current_label = _normalize_chord_label(str(chords[index].get("label") or chords[index].get("chord") or ""))
        if current_label != label_normalized:
            index += 1
            continue
        start_time = float(chords[index].get("time_s", chords[index].get("time", 0.0)) or 0.0)
        next_index = index + 1
        while next_index < len(chords):
            next_label = _normalize_chord_label(str(chords[next_index].get("label") or chords[next_index].get("chord") or ""))
            if next_label != label_normalized:
                spans.append((start_time, float(chords[next_index].get("time_s", chords[next_index].get("time", 0.0)) or start_time)))
                break
            next_index += 1
        index = next_index
    return [span for span in spans if span[1] > span[0]]