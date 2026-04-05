from __future__ import annotations

from pathlib import Path
from typing import Any

from ..runtime.model_cleanup import release_model_memory
from ..runtime.progress import ProgressCallback
from .build_music_feature_layers import TASK as BUILD_MUSIC_FEATURE_LAYERS_TASK
from .energy_layer import TASK as ENERGY_LAYER_TASK
from . import init_song
from .essentia_analysis import TASK as ESSENTIA_ANALYSIS_TASK
from .find_beats import TASK as FIND_BEATS_TASK
from .find_chord_patterns import TASK as FIND_CHORD_PATTERNS_TASK
from .find_chords import TASK as FIND_CHORDS_TASK
from .find_sections import TASK as FIND_SECTIONS_TASK
from .find_song_features import TASK as FIND_SONG_FEATURES_TASK
from .find_stem_patterns import TASK as FIND_STEM_PATTERNS_TASK
from .generate_md import TASK as GENERATE_MD_TASK
from .harmonic_layer import TASK as HARMONIC_LAYER_TASK
from .import_moises_task import TASK as IMPORT_MOISES_TASK
from .split_stems import TASK as SPLIT_STEMS_TASK
from .stereo_analysis import TASK as STEREO_ANALYSIS_TASK
from .symbolic_layer import TASK as SYMBOLIC_LAYER_TASK

def _param(name: str, description: str, *, required: bool = True, default: Any = None) -> dict[str, Any]:
    payload = {"name": name, "description": description, "required": required}
    if default is not None:
        payload["default"] = default
    return payload


def _task(base: dict[str, Any], *, requires: list[str], produces: list[str], notes: list[str] | None = None) -> dict[str, Any]:
    return {**base, "requires": requires, "produces": produces, "notes": notes or []}


TASK_DEFINITIONS = [
    _task(
        {
            "value": "init-song",
            "label": "Init Song",
            "description": "Create the canonical info.json root for a song.",
            "params": [
                _param("song_path", "Absolute or analyzer-visible path to the source song file."),
                _param("meta_path", "Analyzer meta root for generated artifacts.", default="/app/meta"),
            ],
            "runner": init_song.run,
        },
        requires=["source song path"],
        produces=["info.json root"],
        notes=["Creates song_name, song_path, bpm, duration, and the analyzer artifact root."],
    ),
    _task(SPLIT_STEMS_TASK, requires=["source song path", "info.json root"], produces=["stems directory", "info.json stem metadata"], notes=["Runs Demucs and records stems_dir and stems in info.json."]),
    _task(FIND_BEATS_TASK, requires=["source song path", "info.json root"], produces=["reference/beats.json or inferred/beats.<model>.json", "info.json beat metadata"], notes=["Uses Moises beat source when compatible Moises chord data exists."]),
    _task(ESSENTIA_ANALYSIS_TASK, requires=["source song path", "info.json root"], produces=["essentia json artifacts", "optional essentia svg plots", "hints.json", "info.json essentia manifest"], notes=["Reads stems when present. Hints stay analyzer-owned even when supported by Moises-derived sections. Plot generation is opt-in and disabled by default."]),
    _task(FIND_SONG_FEATURES_TASK, requires=["info.json", "canonical beats", "essentia mix artifacts"], produces=["features.json", "info.json feature summary"], notes=["Also uses sections.json and hints.json when present."]),
    _task(STEREO_ANALYSIS_TASK, requires=["features.json", "source song path", "optional stems"], produces=["features.json stereo_analysis payload"], notes=["Adds only notable stereo differences for the mix and available stems using a fixed tag vocabulary."]),
    _task(FIND_CHORDS_TASK, requires=["canonical beats"], produces=["beat-aligned chord metadata", "info.json musical structure metadata"], notes=["Optional enrichment step."]),
    _task(FIND_CHORD_PATTERNS_TASK, requires=["canonical beats with chord labels"], produces=["chord_patterns.json when repeating progressions are found", "info.json artifact reference"], notes=["Uses bar-aware windows, treats seventh chords as triads for comparison, and tolerates small beat-level chord noise on patterns longer than two bars."]),
    _task(FIND_STEM_PATTERNS_TASK, requires=["chord_patterns.json", "stem loudness_envelope artifacts"], produces=["stem_patterns.json when repeating stem profiles are found", "info.json artifact reference"], notes=["Uses chord pattern occurrence windows first, then derives per-stem loudness and envelope profiles without beat alignment."]),
    _task(FIND_SECTIONS_TASK, requires=["canonical beats"], produces=["sections.json", "info.json musical structure metadata"], notes=["Used when analyzer must infer sections or when Moises segments are unavailable."]),
    _task(IMPORT_MOISES_TASK, requires=["moises/chords.json"], produces=["reference/beats.json", "optional sections.json", "info.json beat metadata"], notes=["Moises files are external source-of-truth inputs and are never overwritten or deleted."]),
    _task(HARMONIC_LAYER_TASK, requires=["canonical beats", "optional chord pattern metadata"], produces=["layer_a_harmonic.json"], notes=["Builds a harmonic summary layer from canonical beat and chord artifacts."]),
    _task(SYMBOLIC_LAYER_TASK, requires=["source song path", "canonical beats", "sections.json", "split stems metadata"], produces=["layer_b_symbolic.json"], notes=["Uses Basic Pitch note extraction on harmonic and bass sources and aligns notes to canonical analyzer timing."]),
    _task(ENERGY_LAYER_TASK, requires=["features.json", "hints.json", "sections.json"], produces=["layer_c_energy.json"], notes=["Builds a consolidated energy layer from existing analyzer feature outputs."]),
    _task(BUILD_MUSIC_FEATURE_LAYERS_TASK, requires=["layer_a_harmonic.json", "layer_b_symbolic.json", "layer_c_energy.json"], produces=["music_feature_layers.json"], notes=["Merges layer outputs into one LLM-ready IR used by lighting-score generation."]),
    _task(GENERATE_MD_TASK, requires=["music_feature_layers.json"], produces=["lighting_score.md"], notes=["Uses the merged analyzer IR as the canonical lighting-score input."]),
]
TASKS_BY_TYPE = {task["value"]: task for task in TASK_DEFINITIONS}


def list_task_types() -> list[dict[str, Any]]:
    return [{key: value for key, value in task.items() if key != "runner"} for task in TASK_DEFINITIONS]


def get_task_type(task_type: str) -> dict[str, Any] | None:
    task = TASKS_BY_TYPE.get(task_type)
    if task is None:
        return None
    return {key: value for key, value in task.items() if key != "runner"}


def run_registered_task(task_type: str, params: dict[str, Any], progress_callback: ProgressCallback | None = None) -> Any:
    task = TASKS_BY_TYPE.get(task_type)
    if task is None:
        raise ValueError(f"Unsupported task_type: {task_type}")
    song_path = params.get("song_path")
    if not song_path:
        raise ValueError("Missing required parameter: song_path")
    params = {**params, "song_path": str(Path(song_path).expanduser().resolve())}
    try:
        return task["runner"](params, progress_callback=progress_callback)
    finally:
        release_model_memory()