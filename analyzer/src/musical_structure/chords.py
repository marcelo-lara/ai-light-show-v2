from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

from .io import bass_stem_path, beats_path, dump_json, load_beats
from .labels import bass_note_from_label, normalize_chord_label
from .hf_models import predict_windows
from .registry import ModelCandidate, models_for, serialize_candidates

LOGGER = logging.getLogger(__name__)


def _beat_windows(beats: list[dict[str, Any]], window_s: float) -> list[tuple[float, float, float]]:
    times = [float(row.get("time", 0.0)) for row in beats]
    if not times:
        return []
    median_gap = float(np.median(np.diff(times))) if len(times) > 1 else 0.5
    half_window = max(window_s / 2.0, median_gap)
    return [(max(0.0, time_value - half_window), time_value + half_window, time_value) for time_value in times]


def _attempt_payload(candidate: ModelCandidate, *, ok: bool, error: str | None = None, confidence: dict[str, float | int] | None = None, label_count: int = 0) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": candidate.name,
        "model_id": candidate.model_id,
        "loader": candidate.loader,
        "ok": ok,
        "label_count": label_count,
    }
    if confidence is not None:
        payload["confidence"] = confidence
    if error:
        payload["error"] = error
    return payload


def _run_candidates(audio_path: Path, beats: list[dict[str, Any]], candidates: list[ModelCandidate], normalizer) -> dict[str, Any] | None:
    attempts: list[dict[str, Any]] = []
    for candidate in candidates:
        try:
            windows = _beat_windows(beats, candidate.window_s)
            prediction = predict_windows(candidate, audio_path, windows)
        except Exception as exc:
            LOGGER.warning("Chord model %s failed for %s: %s", candidate.model_id, audio_path.name, exc)
            attempts.append(_attempt_payload(candidate, ok=False, error=str(exc)))
            continue
        labels = [normalizer(str(row.get("label") or "")) for row in prediction["items"]]
        if any(label is not None for label in labels):
            attempts.append(
                _attempt_payload(
                    candidate,
                    ok=True,
                    confidence=prediction.get("confidence"),
                    label_count=sum(1 for label in labels if label not in {None, "N"}),
                )
            )
            return {"candidate": candidate, "labels": labels, "confidence": prediction.get("confidence"), "attempts": attempts}
        attempts.append(_attempt_payload(candidate, ok=False, error="no_usable_labels"))
    return None


def find_chords(
    song_path: str | Path,
    meta_path: str | Path,
    temp_files_root: str | Path,
    output_name: str = "beats.json",
) -> dict[str, Any] | None:
    song_file = Path(song_path).expanduser().resolve()
    beats = load_beats(song_file, meta_path)
    if not beats:
        LOGGER.warning("Missing canonical beats for %s", song_file.name)
        return None
    chord_candidates = models_for("find_chords")
    if not chord_candidates:
        LOGGER.warning("No chord models configured for %s", song_file.name)
        return None
    mix_result = _run_candidates(song_file, beats, chord_candidates, normalize_chord_label)
    if mix_result is None:
        LOGGER.warning("All chord models failed for %s", song_file.name)
        return None
    mix_model = mix_result["candidate"]
    chord_labels = mix_result["labels"]
    bass_file = bass_stem_path(song_file, temp_files_root)
    bass_labels: list[str | None] = [None] * len(beats)
    bass_model_name: str | None = None
    bass_attempts: list[dict[str, Any]] = []
    bass_confidence: dict[str, float | int] | None = None
    if bass_file.exists():
        bass_result = _run_candidates(bass_file, beats, chord_candidates, bass_note_from_label)
        if bass_result is None:
            LOGGER.warning("All bass chord models failed for %s", song_file.name)
        else:
            bass_model_name = bass_result["candidate"].name
            bass_labels = bass_result["labels"]
            bass_confidence = bass_result.get("confidence")
            bass_attempts = bass_result.get("attempts", [])
    else:
        LOGGER.warning("Missing bass stem for %s at %s", song_file.name, bass_file)
    updated = []
    for beat_row, chord_label, bass_label in zip(beats, chord_labels, bass_labels):
        updated.append({**beat_row, "chord": chord_label, "bass": bass_label})
    output_path = beats_path(song_file, meta_path, output_name)
    dump_json(output_path, updated)
    return {
        "beats_file": str(output_path),
        "beat_count": len(updated),
        "mix_model": mix_model.name,
        "bass_model": bass_model_name,
        "method": mix_model.name,
        "confidence": mix_result.get("confidence"),
        "inputs": {
            "mix": str(song_file),
            "bass_stem": str(bass_file),
            "bass_available": bass_file.exists(),
            "bass_used": bass_model_name is not None,
        },
        "attempts": {
            "mix": mix_result.get("attempts", []),
            "bass": bass_attempts,
        },
        "bass_confidence": bass_confidence,
        "candidates": serialize_candidates("find_chords"),
    }