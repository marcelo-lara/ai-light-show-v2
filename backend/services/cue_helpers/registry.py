from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

from models.song.beats import Beat

from .downbeats_and_beats import generate_downbeats_and_beats
from .parcan_echoes import generate_parcan_echoes
from .song_draft import generate_song_draft

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
            {"name": "color", "label": "Color", "type": "color", "default": "#FFFFFF", "required": True},
            {"name": "initial_value", "label": "Initial Brightness", "type": "range", "default": 1.0, "min": 0.05, "max": 1.0, "step": 0.05, "required": True},
            {"name": "delay_beats", "label": "Delay (beats)", "type": "range", "default": 0.5, "min": 0.125, "max": 2.0, "step": 0.125, "required": True},
            {"name": "flash_duration_beats", "label": "Flash Duration (beats)", "type": "range", "default": 0.25, "min": 0.125, "max": 1.0, "step": 0.125, "required": True},
            {"name": "decay_factor", "label": "Decay Factor", "type": "range", "default": 0.7, "min": 0.1, "max": 0.95, "step": 0.05, "required": True},
            {"name": "minimum_value", "label": "Minimum Brightness", "type": "range", "default": 0.2, "min": 0.05, "max": 0.8, "step": 0.05, "required": True},
        ],
        "requires_beats": False,
    },
    {
        "id": "song_draft",
        "label": "Song Draft",
        "description": "Create a draft cue sheet from analyzer beats, sections, and per-stem section features.",
        "mode": "full_song",
        "parameters": [],
        "requires_beats": True,
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
    song: Any | None = None,
    fixtures: List[Any] | None = None,
    pois: List[Dict[str, Any]] | None = None,
    supported_effects=None,
) -> List[Dict[str, Any]]:
    if helper_id == "downbeats_and_beats":
        return generate_downbeats_and_beats(beats, bpm)
    if helper_id == "parcan_echoes":
        return generate_parcan_echoes(bpm, params)
    if helper_id == "song_draft":
        if song is None or fixtures is None or pois is None or supported_effects is None:
            raise ValueError("song_draft_requires_context")
        return generate_song_draft(song, fixtures, pois, supported_effects)
    raise ValueError("unknown_helper_id")