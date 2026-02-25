from __future__ import annotations

from typing import Any, Dict

import essentia.standard as es
import numpy as np

from .common import to_jsonable, warn


def extract_rhythm_descriptors(audio: np.ndarray) -> Dict[str, Any]:
    output_names = [
        "beats_position",
        "confidence",
        "bpm",
        "bpm_estimates",
        "bpm_intervals",
        "first_peak_bpm",
        "first_peak_spread",
        "first_peak_weight",
        "second_peak_bpm",
        "second_peak_spread",
        "second_peak_weight",
        "histogram",
    ]

    result: Dict[str, Any] = {
        "beats_position": [],
        "confidence": 0.0,
        "bpm": 0.0,
        "bpm_estimates": [],
        "bpm_intervals": [],
        "first_peak_bpm": 0.0,
        "first_peak_spread": 0.0,
        "first_peak_weight": 0.0,
        "second_peak_bpm": 0.0,
        "second_peak_spread": 0.0,
        "second_peak_weight": 0.0,
        "histogram": [],
    }

    try:
        values = es.RhythmDescriptors()(audio)
        if isinstance(values, tuple) and len(values) == len(output_names):
            mapped = dict(zip(output_names, values))
            mapped_json = to_jsonable(mapped)
            beats_position = mapped_json.get("beats_position", [])
            if beats_position:
                return mapped_json
            warn("RhythmDescriptors returned empty beats; using fallback extractor path")
        else:
            warn("RhythmDescriptors returned an unexpected output shape; using fallback extractor path")
    except Exception as exc:
        warn(f"RhythmDescriptors failed: {exc}; using fallback extractor path")

    try:
        bpm, ticks, confidence, estimates, bpm_intervals = es.RhythmExtractor2013()(audio)
        (
            first_peak_bpm,
            first_peak_weight,
            first_peak_spread,
            second_peak_bpm,
            second_peak_weight,
            second_peak_spread,
            histogram,
        ) = es.BpmHistogramDescriptors()(bpm_intervals)

        fallback = {
            "beats_position": ticks,
            "confidence": confidence,
            "bpm": bpm,
            "bpm_estimates": estimates,
            "bpm_intervals": bpm_intervals,
            "first_peak_bpm": first_peak_bpm,
            "first_peak_spread": first_peak_spread,
            "first_peak_weight": first_peak_weight,
            "second_peak_bpm": second_peak_bpm,
            "second_peak_spread": second_peak_spread,
            "second_peak_weight": second_peak_weight,
            "histogram": histogram,
        }
        return to_jsonable(fallback)
    except Exception as exc:
        warn(f"Fallback rhythm descriptors failed: {exc}")
        return result
