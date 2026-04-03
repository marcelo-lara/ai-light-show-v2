from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .hf_models import predict_sections
from .io import dump_json, load_beats, sections_path
from .labels import normalize_section_label
from .registry import ModelCandidate, models_for, serialize_candidates

LOGGER = logging.getLogger(__name__)


def _attempt_payload(candidate: ModelCandidate, *, ok: bool, error: str | None = None, confidence: dict[str, float | int] | None = None, section_count: int = 0) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": candidate.name,
        "model_id": candidate.model_id,
        "loader": candidate.loader,
        "ok": ok,
        "section_count": section_count,
    }
    if confidence is not None:
        payload["confidence"] = confidence
    if error:
        payload["error"] = error
    return payload


def _collapse_sections(predicted: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for segment in predicted:
        label = normalize_section_label(str(segment.get("label") or segment.get("name") or ""))
        start_s = float(segment.get("start", segment.get("start_time_s", 0.0)) or 0.0)
        end_s = float(segment.get("end", segment.get("end_time_s", start_s)) or start_s)
        if label is None or end_s <= start_s:
            continue
        rows.append({"start": start_s, "end": end_s, "label": label, "description": "", "hints": []})
    return rows


def _run_candidates(song_file: Path, candidates: list[ModelCandidate]) -> dict[str, Any] | None:
    attempts: list[dict[str, Any]] = []
    for candidate in candidates:
        try:
            prediction = predict_sections(candidate, song_file)
        except Exception as exc:
            LOGGER.warning("Section model %s failed for %s: %s", candidate.model_id, song_file.name, exc)
            attempts.append(_attempt_payload(candidate, ok=False, error=str(exc)))
            continue
        sections = _collapse_sections(prediction["items"])
        if sections:
            attempts.append(
                _attempt_payload(
                    candidate,
                    ok=True,
                    confidence=prediction.get("confidence"),
                    section_count=len(sections),
                )
            )
            return {"candidate": candidate, "sections": sections, "confidence": prediction.get("confidence"), "attempts": attempts}
        attempts.append(_attempt_payload(candidate, ok=False, error="no_usable_sections"))
    return None


def find_sections(song_path: str | Path, meta_path: str | Path, output_name: str = "sections.json") -> dict[str, Any] | None:
    song_file = Path(song_path).expanduser().resolve()
    beats = load_beats(song_file, meta_path)
    if not beats:
        LOGGER.warning("Missing canonical beats for %s", song_file.name)
        return None
    section_candidates = models_for("find_sections")
    if not section_candidates:
        LOGGER.warning("No section models configured for %s", song_file.name)
        return None
    result = _run_candidates(song_file, section_candidates)
    if result is None:
        LOGGER.warning("All section models failed for %s", song_file.name)
        return None
    model = result["candidate"]
    sections = result["sections"]
    output_path = sections_path(song_file, meta_path, output_name)
    dump_json(output_path, sections)
    return {
        "sections_file": str(output_path),
        "section_count": len(sections),
        "model": model.name,
        "method": model.name,
        "confidence": result.get("confidence"),
        "inputs": {"mix": str(song_file), "beat_count": len(beats)},
        "attempts": result.get("attempts", []),
        "candidates": serialize_candidates("find_sections"),
    }