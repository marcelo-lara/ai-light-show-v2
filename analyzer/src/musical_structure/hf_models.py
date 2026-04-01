from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import librosa

from .registry import ModelCandidate

os.environ["CUDA_VISIBLE_DEVICES"] = ""

_AUDIO_CACHE: dict[str, tuple[object, object, int, dict[int, str]]] = {}
_REMOTE_CACHE: dict[str, object] = {}


def _confidence_summary(scores: list[float]) -> dict[str, float | int] | None:
    if not scores:
        return None
    return {
        "count": len(scores),
        "mean": round(sum(scores) / len(scores), 4),
        "min": round(min(scores), 4),
        "max": round(max(scores), 4),
    }


def _load_audio_bundle(candidate: ModelCandidate) -> tuple[object, object, int, dict[int, str]]:
    if candidate.model_id in _AUDIO_CACHE:
        return _AUDIO_CACHE[candidate.model_id]
    from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

    extractor = AutoFeatureExtractor.from_pretrained(candidate.model_id, trust_remote_code=candidate.trust_remote_code)
    model = AutoModelForAudioClassification.from_pretrained(candidate.model_id, trust_remote_code=candidate.trust_remote_code)
    if hasattr(model, "to"):
        model.to("cpu")
    model.eval()
    bundle = (extractor, model, int(getattr(extractor, "sampling_rate", 16000)), dict(getattr(model.config, "id2label", {})))
    _AUDIO_CACHE[candidate.model_id] = bundle
    return bundle


def _load_remote_model(candidate: ModelCandidate) -> object:
    if candidate.model_id in _REMOTE_CACHE:
        return _REMOTE_CACHE[candidate.model_id]
    from transformers import AutoModel

    model = AutoModel.from_pretrained(candidate.model_id, trust_remote_code=candidate.trust_remote_code)
    if hasattr(model, "to"):
        model.to("cpu")
    if hasattr(model, "eval"):
        model.eval()
    _REMOTE_CACHE[candidate.model_id] = model
    return model


def predict_windows(candidate: ModelCandidate, audio_path: Path, windows: list[tuple[float, float, float]]) -> dict[str, Any]:
    if candidate.loader != "audio-classification":
        raise RuntimeError(f"Unsupported chord loader: {candidate.loader}")
    extractor, model, sample_rate, id_to_label = _load_audio_bundle(candidate)
    import torch

    audio, _ = librosa.load(str(audio_path), sr=sample_rate, mono=True)
    items: list[dict[str, float | str]] = []
    scores: list[float] = []
    with torch.no_grad():
        for start_s, end_s, center_s in windows:
            start_index = max(0, int(start_s * sample_rate))
            end_index = min(audio.shape[0], int(end_s * sample_rate))
            if end_index <= start_index:
                continue
            inputs = extractor(audio[start_index:end_index], sampling_rate=sample_rate, return_tensors="pt", padding=True)
            logits = model(**inputs).logits[0]
            probs = torch.softmax(logits, dim=-1)
            label_index = int(torch.argmax(probs).item())
            score = float(probs[label_index].item())
            scores.append(score)
            items.append({"label": id_to_label.get(label_index, str(label_index)), "score": score, "time": center_s})
    if not items:
        raise RuntimeError("Model returned no chord windows")
    return {"items": items, "confidence": _confidence_summary(scores)}


def predict_sections(candidate: ModelCandidate, audio_path: Path) -> dict[str, Any]:
    if candidate.loader != "remote-segmentation":
        raise RuntimeError(f"Unsupported section loader: {candidate.loader}")
    model = _load_remote_model(candidate)
    segments_output = model(audio_file=str(audio_path), return_segments=True)
    segments = getattr(segments_output, "segments", segments_output)
    items = list(segments) if isinstance(segments, list) else []
    if not items:
        raise RuntimeError("Model returned no sections")
    confidence = None
    try:
        import torch

        raw_output = model(audio_file=str(audio_path), return_segments=False)
        class_logits = getattr(raw_output, "class_logits", None)
        if class_logits is not None:
            probs = torch.softmax(class_logits, dim=-1)
            max_probs = probs.max(dim=-1).values
            confidence = _confidence_summary([float(value) for value in max_probs.detach().cpu().tolist()])
    except Exception:
        confidence = None
    return {"items": items, "confidence": confidence}