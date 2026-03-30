from __future__ import annotations

from typing import Any

from models.song.analysis_contract import SectionAnalysis


def section_palette(section: SectionAnalysis) -> tuple[dict[str, int], str]:
    level = str(section.energy.get("level") or "mid")
    trend = str(section.energy.get("trend") or "flat")
    if level == "high":
        return ({"red": 255, "green": 64, "blue": 16}, "#FFFFFF")
    if trend == "swell":
        return ({"red": 13, "green": 59, "blue": 255}, "#FFFFFF")
    if level == "low":
        return ({"red": 0, "green": 128, "blue": 255}, "#FFFFFF")
    return ({"red": 13, "green": 59, "blue": 255}, "#FFFFFF")


def beat_duration_s(section_beats: list[Any], bpm: float) -> float:
    if len(section_beats) > 1:
        deltas = [max(0.05, float(section_beats[index + 1].time) - float(section_beats[index].time)) for index in range(len(section_beats) - 1)]
        return sum(deltas) / len(deltas)
    if bpm > 0.0:
        return 60.0 / bpm
    return 0.5


def accent_times(section: SectionAnalysis, preferred_parts: tuple[str, ...]) -> list[float]:
    for part in preferred_parts:
        accents = section.stem_accents.get(part) or []
        if accents:
            return [float(accent.time) for accent in accents]
    return [float(event.time_s) for event in section.events if event.time_s is not None]