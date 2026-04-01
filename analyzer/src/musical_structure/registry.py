from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ModelCandidate:
    name: str
    model_id: str
    loader: str
    window_s: float
    stride_s: float
    trust_remote_code: bool = False


DEFAULT_MODELS = {
    "find_chords": [
        ModelCandidate(
            name="ast-chordy",
            model_id="andrewmcgill04/ast-finetuned-audioset-10-10-0.4593-chordy",
            loader="audio-classification",
            window_s=6.0,
            stride_s=2.0,
        )
    ],
    "find_sections": [
        ModelCandidate(
            name="music-section-detection",
            model_id="ArseniiChstiakovml/MusicSectionDetection",
            loader="remote-segmentation",
            window_s=0.0,
            stride_s=0.0,
            trust_remote_code=True,
        )
    ],
}


def _parse_candidates(raw: str) -> list[ModelCandidate]:
    payload = json.loads(raw)
    if not isinstance(payload, list):
        return []
    candidates: list[ModelCandidate] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or row.get("model_id") or "").strip()
        model_id = str(row.get("model_id") or "").strip()
        if not name or not model_id:
            continue
        candidates.append(
            ModelCandidate(
                name=name,
                model_id=model_id,
                loader=str(row.get("loader") or "audio-classification").strip(),
                window_s=float(row.get("window_s", 8.0)),
                stride_s=float(row.get("stride_s", 2.0)),
                trust_remote_code=bool(row.get("trust_remote_code", False)),
            )
        )
    return candidates


def models_for(task_type: str) -> list[ModelCandidate]:
    env_var = f"ANALYZER_{task_type.upper()}_MODELS_JSON"
    raw = os.environ.get(env_var)
    if raw:
        parsed = _parse_candidates(raw)
        if parsed:
            return parsed
    return list(DEFAULT_MODELS.get(task_type, []))


def serialize_candidates(task_type: str) -> list[dict[str, str | float]]:
    return [asdict(candidate) for candidate in models_for(task_type)]