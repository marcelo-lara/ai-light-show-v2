from __future__ import annotations

from collections import Counter
import re
from typing import Any

MAX_PATTERN_BARS = 8
FOUR_BAR_PRIORITY = 4


def find_chord_patterns(beats: list[dict[str, Any]], *, beats_file: str | None = None) -> dict[str, Any] | None:
    bars = _build_bars(beats)
    if len(bars) < 2:
        return None
    covered: set[int] = set()
    patterns: list[dict[str, Any]] = []
    while True:
        candidate = _best_candidate(bars, covered)
        if candidate is None:
            break
        patterns.append(_pattern_payload(candidate, len(patterns)))
        for occurrence in candidate["occurrences"]:
            covered.update(range(occurrence["start_index"], occurrence["start_index"] + candidate["bar_count"]))
    if not patterns:
        return None
    return {
        "beats_file": beats_file,
        "pattern_count": len(patterns),
        "settings": {"priority_bars": FOUR_BAR_PRIORITY, "max_pattern_bars": MAX_PATTERN_BARS, "noise_tolerance_beats": 3},
        "patterns": patterns,
    }


def _build_bars(beats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[int, dict[str, list[float | str | None]]] = {}
    for row in beats:
        if not isinstance(row, dict):
            continue
        bar = int(row.get("bar") or 0)
        beat = int(row.get("beat") or 0)
        if bar < 1 or beat < 1 or beat > 4:
            continue
        slot = grouped.setdefault(bar, {"beats": [None, None, None, None], "times": [None, None, None, None]})
        slot["beats"][beat - 1] = _normalize_chord(row.get("chord"))
        time_value = row.get("time")
        slot["times"][beat - 1] = float(time_value) if isinstance(time_value, (int, float)) else None
    bars: list[dict[str, Any]] = []
    for bar_number in sorted(grouped):
        beats_in_bar = list(grouped[bar_number]["beats"])
        times = [value for value in grouped[bar_number]["times"] if isinstance(value, float)]
        if not times:
            continue
        bars.append({"bar": bar_number, "beats": beats_in_bar, "display": _display_bar(beats_in_bar), "start_time": min(times), "end_time": max(times)})
    return bars


def _normalize_chord(label: Any) -> str | None:
    if not isinstance(label, str) or not label or label == "N":
        return None
    match = re.match(r"^([A-G](?:#|b)?)(.*)$", label.strip())
    if not match:
        return label.strip() or None
    root, suffix = match.groups()
    normalized_suffix = suffix.replace("maj7", "maj").replace("min7", "m").replace("m7", "m").replace("M7", "maj").replace("7", "")
    return f"{root}{normalized_suffix}".strip() or root


def _display_bar(labels: list[str | None]) -> str:
    compact: list[str] = []
    for label in labels:
        if label and (not compact or compact[-1] != label):
            compact.append(label)
    return "-".join(compact)


def _best_candidate(bars: list[dict[str, Any]], covered: set[int]) -> dict[str, Any] | None:
    for bar_count in _candidate_lengths(len(bars)):
        best_for_length: dict[str, Any] | None = None
        for start_index in range(0, len(bars) - bar_count + 1):
            candidate = _group_candidate(bars, covered, start_index, bar_count)
            if candidate is None:
                continue
            if best_for_length is None or candidate["score"] > best_for_length["score"]:
                best_for_length = candidate
        if best_for_length is not None:
            return best_for_length
    return None


def _candidate_lengths(total_bars: int) -> list[int]:
    max_bars = min(MAX_PATTERN_BARS, total_bars // 2)
    lengths = list(range(2, max_bars + 1))
    return sorted(lengths, key=lambda value: (value != FOUR_BAR_PRIORITY, abs(value - FOUR_BAR_PRIORITY), -value))


def _group_candidate(bars: list[dict[str, Any]], covered: set[int], start_index: int, bar_count: int) -> dict[str, Any] | None:
    if not _window_available(covered, start_index, bar_count):
        return None
    base = bars[start_index : start_index + bar_count]
    if not any(label for bar in base for label in bar["beats"]):
        return None
    occurrences: list[dict[str, Any]] = []
    next_index = start_index
    for index in range(start_index, len(bars) - bar_count + 1):
        if index < next_index or not _window_available(covered, index, bar_count):
            continue
        window = bars[index : index + bar_count]
        mismatch_count = _mismatch_count(base, window)
        if mismatch_count <= _allowed_mismatches(bar_count):
            occurrences.append({"start_index": index, "bars": window, "mismatch_count": mismatch_count})
            next_index = index + bar_count
    if len(occurrences) < 2:
        return None
    mismatch_total = sum(item["mismatch_count"] for item in occurrences)
    coverage = len(occurrences) * bar_count
    repetition = (len(occurrences) - 1) * bar_count
    priority_bonus = 6 if bar_count == FOUR_BAR_PRIORITY else max(0, 4 - abs(bar_count - FOUR_BAR_PRIORITY))
    score = coverage * 6 + repetition * 4 + bar_count * 6 + priority_bonus - mismatch_total * 4
    return {"bar_count": bar_count, "occurrences": occurrences, "sequence": _display_window(_representative_window(occurrences, bar_count)), "score": score}


def _window_available(covered: set[int], start_index: int, bar_count: int) -> bool:
    return all(index not in covered for index in range(start_index, start_index + bar_count))


def _mismatch_count(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> int:
    left_beats = [label for bar in left for label in bar["beats"]]
    right_beats = [label for bar in right for label in bar["beats"]]
    return sum(1 for a, b in zip(left_beats, right_beats) if a != b)


def _allowed_mismatches(bar_count: int) -> int:
    return 3 if bar_count > 2 else 0


def _display_window(window: list[dict[str, Any]]) -> str:
    return "|".join(bar["display"] or "N" for bar in window)


def _representative_window(occurrences: list[dict[str, Any]], bar_count: int) -> list[dict[str, Any]]:
    flattened = [[label for bar in occurrence["bars"] for label in bar["beats"]] for occurrence in occurrences]
    primary = flattened[min(range(len(occurrences)), key=lambda index: occurrences[index]["mismatch_count"])]
    representative: list[str | None] = []
    for index in range(bar_count * 4):
        labels = [beats[index] for beats in flattened if beats[index] is not None]
        if not labels:
            representative.append(None)
            continue
        counts = Counter(labels).most_common()
        winner = counts[0][0]
        if len(counts) > 1 and counts[0][1] == counts[1][1] and primary[index] in {item[0] for item in counts if item[1] == counts[0][1]}:
            winner = primary[index]
        representative.append(winner)
    return [{"beats": representative[index : index + 4], "display": _display_bar(representative[index : index + 4])} for index in range(0, len(representative), 4)]


def _pattern_payload(candidate: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "id": f"pattern_{chr(ord('A') + index)}",
        "label": chr(ord("A") + index),
        "bar_count": candidate["bar_count"],
        "sequence": candidate["sequence"],
        "occurrence_count": len(candidate["occurrences"]),
        "occurrences": [
            {
                "start_bar": occurrence["bars"][0]["bar"],
                "end_bar": occurrence["bars"][-1]["bar"],
                "start_time": occurrence["bars"][0]["start_time"],
                "end_time": occurrence["bars"][-1]["end_time"],
                "mismatch_count": occurrence["mismatch_count"],
                "sequence": _display_window(occurrence["bars"]),
            }
            for occurrence in candidate["occurrences"]
        ],
    }