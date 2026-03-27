from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

from models.song.beats import Beat

from .downbeats_and_beats import generate_downbeats_and_beats
from .parcan_echoes import generate_parcan_echoes

_HELPERS: List[Dict[str, Any]] = [
    {
        "id": "downbeats_and_beats",
        "label": "DownBeats and Beats",
        "description": "Flash mini beams on downbeats, then chase blue on parcans through beats",
        "mode": "full_song",
        "parameters": [],
        "requires_beats": True,
    },
    {
        "id": "parcan_echoes",
        "label": "Parcan Echoes",
        "description": "Alternate parcan_l and parcan_r flashes with color and decaying brightness.",
        "mode": "parameterized",
        "parameters": [
            {"name": "start_time_ms", "label": "Start Time (ms)", "type": "number", "default": 0, "min": 0, "step": 50, "required": True},
            {"name": "color", "label": "Color", "type": "text", "default": "#FFFFFF", "required": True},
            {"name": "initial_value", "label": "Initial Brightness", "type": "range", "default": 1.0, "min": 0.05, "max": 1.0, "step": 0.05, "required": True},
            {"name": "delay_beats", "label": "Delay (beats)", "type": "range", "default": 0.5, "min": 0.125, "max": 2.0, "step": 0.125, "required": True},
            {"name": "flash_duration_beats", "label": "Flash Duration (beats)", "type": "range", "default": 0.25, "min": 0.125, "max": 1.0, "step": 0.125, "required": True},
            {"name": "decay_factor", "label": "Decay Factor", "type": "range", "default": 0.7, "min": 0.1, "max": 0.95, "step": 0.05, "required": True},
            {"name": "minimum_value", "label": "Minimum Brightness", "type": "range", "default": 0.2, "min": 0.05, "max": 0.8, "step": 0.05, "required": True},
        ],
        "requires_beats": False,
    },
]


def build_cue_helper_definitions() -> List[Dict[str, Any]]:
    return [deepcopy({key: value for key, value in helper.items() if key != "requires_beats"}) for helper in _HELPERS]


def get_cue_helper_definition(helper_id: str) -> Dict[str, Any] | None:
    helper_key = str(helper_id or "").strip()
    for helper in _HELPERS:
        if helper["id"] == helper_key:
            return deepcopy(helper)
    return None


def generate_cue_helper_entries(
    helper_id: str,
    *,
    beats: List[Beat],
    bpm: float,
    params: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    if helper_id == "downbeats_and_beats":
        return generate_downbeats_and_beats(beats, bpm)
    if helper_id == "parcan_echoes":
        return generate_parcan_echoes(bpm, params)
    raise ValueError("unknown_helper_id")