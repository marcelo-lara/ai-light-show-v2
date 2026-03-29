from __future__ import annotations

from typing import Any


MERGE_WINDOW_S = 0.35
MIN_SPACING_S = 0.5


def _smooth(values: list[float], radius: int = 2) -> list[float]:
    return [sum(values[max(0, i - radius):min(len(values), i + radius + 1)]) / len(values[max(0, i - radius):min(len(values), i + radius + 1)]) for i in range(len(values))]


def _normalize_sections(sections: list[dict[str, Any]] | None, parts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for index, section in enumerate(sections or [], start=1):
        start_value = float(section.get("start_s", section.get("start", 0.0)) or 0.0)
        end_value = float(section.get("end_s", section.get("end", start_value)) or start_value)
        normalized.append({"name": str(section.get("name") or section.get("label") or f"Section {index}"), "start_s": round(start_value, 3), "end_s": round(max(end_value, start_value), 3)})
    if normalized:
        return sorted(normalized, key=lambda item: item["start_s"])
    mix = (parts.get("mix") or {}).get("loudness_envelope") or {}
    times = [float(value) for value in mix.get("times") or []]
    if len(times) >= 2:
        return [{"name": "Song", "start_s": round(times[0], 3), "end_s": round(times[-1], 3)}]
    return []


def _detect_part_events(part: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    times = [float(value) for value in payload.get("times") or []]
    loudness = [float(value) for value in payload.get("loudness") or []]
    if len(times) < 2 or len(times) != len(loudness):
        return []
    smoothed = _smooth(loudness)
    value_range = max(smoothed) - min(smoothed)
    if value_range <= 1e-6:
        return []
    deltas = [smoothed[index] - smoothed[index - 1] for index in range(1, len(smoothed))]
    ranked = sorted(abs(delta) for delta in deltas)
    threshold = max(value_range * 0.18, ranked[int(0.75 * (len(ranked) - 1))], 0.04)
    events: list[dict[str, Any]] = []
    last_time = -1.0
    spike_times: set[float] = set()
    for index in range(1, len(smoothed) - 1):
        rise = smoothed[index] - smoothed[index - 1]
        drop = smoothed[index + 1] - smoothed[index]
        if rise < threshold or drop > -threshold * 0.7 or times[index + 1] - times[index - 1] > 1.0:
            continue
        time_s = round(times[index], 3)
        events.append({"time_s": time_s, "part": part, "kind": "sudden_spike", "strength": round(max(abs(rise), abs(drop)) / value_range, 3)})
        spike_times.add(time_s)
        last_time = times[index]
    for index, delta in enumerate(deltas, start=1):
        time_s = round(times[index], 3)
        strength = abs(delta) / value_range
        if abs(delta) < threshold or times[index] - last_time < MIN_SPACING_S or time_s in spike_times:
            continue
        prev_abs = abs(deltas[index - 2]) if index > 1 else -1.0
        next_abs = abs(deltas[index]) if index < len(deltas) else -1.0
        if abs(delta) < prev_abs or abs(delta) < next_abs:
            continue
        events.append({"time_s": time_s, "part": part, "kind": "rise" if delta > 0 else "drop", "strength": round(strength, 3)})
        last_time = times[index]
    return events


def _merge_events(raw_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[list[dict[str, Any]]] = []
    for event in sorted(raw_events, key=lambda item: (item["time_s"], item["part"])):
        if not merged or event["time_s"] - merged[-1][-1]["time_s"] > MERGE_WINDOW_S:
            merged.append([event])
            continue
        merged[-1].append(event)
    hints: list[dict[str, Any]] = []
    for group in merged:
        contributors = sorted(group, key=lambda item: (-item["strength"], item["part"]))
        kinds = {item["kind"] for item in contributors}
        rise_strength = sum(item["strength"] for item in contributors if item["kind"] == "rise")
        drop_strength = sum(item["strength"] for item in contributors if item["kind"] == "drop")
        if "sudden_spike" in kinds:
            kind = "sudden_spike"
        elif rise_strength > drop_strength * 1.15:
            kind = "rise"
        elif drop_strength > rise_strength * 1.15:
            kind = "drop"
        else:
            continue
        total_strength = max(sum(item["strength"] for item in contributors), 1e-6)
        hints.append({"time_s": round(sum(item["time_s"] * item["strength"] for item in contributors) / total_strength, 3), "kind": kind, "strength": round(max(item["strength"] for item in contributors), 3), "dominant_part": contributors[0]["part"], "parts": sorted({item["part"] for item in contributors})})
    return hints


def _section_sustain(section: dict[str, Any], mix_payload: dict[str, Any]) -> dict[str, Any] | None:
    times = [float(value) for value in mix_payload.get("times") or []]
    loudness = [float(value) for value in mix_payload.get("loudness") or []]
    if len(times) < 3 or len(times) != len(loudness):
        return None
    smoothed = _smooth(loudness)
    selected = [(time_s, value) for time_s, value in zip(times, smoothed) if section["start_s"] <= time_s <= section["end_s"]]
    if len(selected) < 3:
        return None
    values = [value for _, value in selected]
    plateau_values = values[1:-1] if len(values) > 4 else values[1:] if len(values) > 3 else values
    global_values = sorted(smoothed)
    high_threshold = global_values[int(0.5 * (len(global_values) - 1))]
    mean_value = sum(plateau_values) / len(plateau_values)
    mean_delta = sum(abs(plateau_values[index] - plateau_values[index - 1]) for index in range(1, len(plateau_values))) / max(len(plateau_values) - 1, 1)
    value_range = max(smoothed) - min(smoothed)
    if mean_value < high_threshold or value_range <= 1e-6 or mean_delta > max(value_range * 0.08, 0.01) or max(plateau_values) - min(plateau_values) > max(value_range * 0.18, 0.03):
        return None
    return {"kind": "sustain", "start_s": section["start_s"], "end_s": section["end_s"], "strength": round((mean_value - min(smoothed)) / value_range, 3), "dominant_part": "mix", "parts": ["mix"]}


def build_loudness_hints(parts: dict[str, dict[str, Any]], sections: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    raw_events: list[dict[str, Any]] = []
    for part, artifacts in parts.items():
        raw_events.extend(_detect_part_events(part, artifacts.get("loudness_envelope") or {}))
    merged_events = _merge_events(raw_events)
    mix_payload = (parts.get("mix") or {}).get("loudness_envelope") or {}
    payload: list[dict[str, Any]] = []
    for section in _normalize_sections(sections, parts):
        hints = [event for event in merged_events if section["start_s"] <= event["time_s"] < section["end_s"]]
        sustain = _section_sustain(section, mix_payload)
        if sustain is not None:
            hints.append(sustain)
        hints.sort(key=lambda item: (float(item.get("time_s", item.get("start_s", 0.0))), item["kind"]))
        payload.append({"name": section["name"], "start_s": section["start_s"], "end_s": section["end_s"], "hints": hints})
    return payload