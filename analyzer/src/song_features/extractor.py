from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any

import librosa
import numpy as np

from src.song_meta import load_json_file, load_list_file, load_sections, song_meta_dir, song_name
from src.song_features.stem_accents import build_stem_beat_profiles, merge_low_windows, summarize_stem_accents, summarize_stem_dips

META_PATH = os.environ.get("META_PATH", "/app/meta")
LOGGER = logging.getLogger(__name__)
MODEL_ID = os.environ.get("SONG_FEATURES_MODEL_ID", "mtg-upf/discogs-maest-30s-pw-129e")
_MODEL_CACHE: tuple[Any, Any, int] | None = None
_MODEL_FAILED = False


TIME_KEYS = {"time", "start_s", "end_s", "peak_time", "duration_s"}


def _round_floats(value: Any, *, key: str | None = None) -> Any:
    if isinstance(value, float):
        return round(value, 2 if key in TIME_KEYS else 3)
    if isinstance(value, dict):
        return {child_key: _round_floats(item, key=child_key) for child_key, item in value.items()}
    if isinstance(value, list):
        return [_round_floats(item, key=key) for item in value]
    return value


def _dump_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_round_floats(payload), indent=2), encoding="utf-8")


def _load_essentia_artifact(essentia_dir: Path, part: str, artifact: str) -> dict[str, Any] | None:
    if part == "mix":
        candidates = [essentia_dir / f"{artifact}.json"]
    else:
        candidates = [
            essentia_dir / f"{part}_{artifact}.json",
            essentia_dir / f"{artifact}.{part}.json",
            essentia_dir / f"{artifact}_{part}.json",
        ]
    for path in candidates:
        if path.exists():
            payload = load_json_file(path)
            return payload if isinstance(payload, dict) else None
    LOGGER.warning("Missing Essentia artifact for part=%s artifact=%s", part, artifact)
    return None


def _window_mask(times: np.ndarray, start_s: float, end_s: float) -> np.ndarray:
    return (times >= start_s) & (times <= end_s)


def _shape_label(values: np.ndarray) -> str | None:
    if values.size < 3:
        return None
    peak_index = int(np.argmax(values))
    valley_index = int(np.argmin(values))
    slope = float(np.polyfit(np.arange(values.size), values, 1)[0]) if values.size >= 2 else 0.0
    if peak_index > values.size * 0.65 and slope > 0:
        return "build"
    if peak_index < values.size * 0.35 and slope < 0:
        return "release"
    if values.size * 0.35 < peak_index < values.size * 0.65:
        return "swell"
    if values.size * 0.35 < valley_index < values.size * 0.65:
        return "valley"
    return "plateau"


def _energy_label(value: float, low: float, high: float) -> str:
    if value <= low:
        return "low"
    if value >= high:
        return "high"
    return "mid"


def _part_strengths(essentia_dir: Path, start_s: float, end_s: float) -> list[dict[str, Any]]:
    strengths: list[dict[str, Any]] = []
    for part in ["mix", "bass", "drums", "vocals", "other"]:
        payload = _load_essentia_artifact(essentia_dir, part, "loudness_envelope")
        if not payload:
            continue
        times = np.asarray(payload.get("times") or [], dtype=float)
        loudness = np.asarray(payload.get("loudness") or [], dtype=float)
        values = loudness[_window_mask(times, start_s, end_s)] if times.size == loudness.size else np.asarray([], dtype=float)
        if values.size:
            strengths.append({"part": part, "mean": float(np.mean(values)), "peak": float(np.max(values))})
    total = sum(item["mean"] for item in strengths) or 1.0
    for item in strengths:
        item["share"] = item["mean"] / total
    return sorted(strengths, key=lambda item: item["share"], reverse=True)


def _phrase_windows(section: dict[str, Any], beat_rows: list[dict[str, Any]], hint_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    start_s = float(section["start_s"])
    end_s = float(section["end_s"])
    anchors = {start_s, end_s}
    anchors.update(float(row["time"]) for row in beat_rows if row.get("beat") == 1 and start_s <= float(row.get("time", -1.0)) <= end_s)
    for hint in hint_rows:
        if hint.get("kind") in {"sudden_spike", "drop"}:
            anchors.add(float(hint.get("time_s", start_s)))
    points = sorted(value for value in anchors if start_s <= value <= end_s)
    windows: list[dict[str, Any]] = []
    for index in range(len(points) - 1):
        window_start = round(points[index], 3)
        window_end = round(points[index + 1], 3)
        if window_end - window_start >= 1.5:
            windows.append({"start_s": window_start, "end_s": window_end})
    return windows


def _load_model() -> tuple[Any, Any, int] | None:
    global _MODEL_CACHE, _MODEL_FAILED
    if _MODEL_CACHE is not None:
        return _MODEL_CACHE
    if _MODEL_FAILED:
        return None
    try:
        from transformers import AutoFeatureExtractor, AutoModelForAudioClassification
        import torch

        extractor = AutoFeatureExtractor.from_pretrained(MODEL_ID, trust_remote_code=True)
        model = AutoModelForAudioClassification.from_pretrained(MODEL_ID, trust_remote_code=True)
        model.eval()
        if torch.cuda.is_available():
            model = model.to("cuda")
        _MODEL_CACHE = (extractor, model, int(getattr(extractor, "sampling_rate", 16000)))
        return _MODEL_CACHE
    except Exception as exc:
        LOGGER.warning("Could not load semantic music model %s: %s", MODEL_ID, exc)
        _MODEL_FAILED = True
        return None


def _model_tags(song_path: Path, start_s: float | None = None, end_s: float | None = None) -> dict[str, Any]:
    loaded = _load_model()
    if loaded is None:
        return {"available": False, "model_id": MODEL_ID, "tags": []}
    extractor, model, sample_rate = loaded
    try:
        import torch

        offset = max(float(start_s or 0.0), 0.0)
        duration = None if end_s is None else max(float(end_s) - offset, 1.0)
        audio, _ = librosa.load(str(song_path), sr=sample_rate, mono=True, offset=offset, duration=duration)
        if audio.size == 0:
            return {"available": False, "model_id": MODEL_ID, "tags": []}
        inputs = extractor(audio, sampling_rate=sample_rate, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = {key: value.to("cuda") for key, value in inputs.items()}
        with torch.no_grad():
            logits = model(**inputs).logits[0]
        if getattr(model.config, "problem_type", "") == "multi_label_classification":
            scores = torch.sigmoid(logits)
        else:
            scores = torch.softmax(logits, dim=-1)
        top_values, top_indices = torch.topk(scores, k=min(5, int(scores.shape[-1])))
        tags = [
            {"label": model.config.id2label[int(index)], "score": float(value)}
            for value, index in zip(top_values.cpu().tolist(), top_indices.cpu().tolist())
        ]
        return {"available": True, "model_id": MODEL_ID, "tags": tags}
    except Exception as exc:
        LOGGER.warning("Could not infer semantic tags for %s: %s", song_path.name, exc)
        return {"available": False, "model_id": MODEL_ID, "tags": []}


def find_song_features(song_path: str | Path, meta_path: str | Path = META_PATH) -> Path | None:
    song_path = Path(song_path).expanduser().resolve()
    meta_dir = song_meta_dir(song_path, meta_path)
    info_path = meta_dir / "info.json"
    if not info_path.exists():
        LOGGER.warning("Missing info.json for %s", song_path.name)
        return None
    info_payload = load_json_file(info_path)
    mix_loudness = _load_essentia_artifact(meta_dir / "essentia", "mix", "loudness_envelope")
    mix_rhythm = _load_essentia_artifact(meta_dir / "essentia", "mix", "rhythm")
    if not mix_loudness or not mix_rhythm:
        LOGGER.warning("Missing required Essentia mix artifacts for %s", song_path.name)
        return None

    beats = load_list_file(meta_dir / "beats.json")
    sections = load_sections(meta_dir)
    hint_rows = load_list_file(meta_dir / "hints.json")
    stem_profiles = build_stem_beat_profiles(meta_dir, beats)
    hints_by_section = {
        (row.get("name"), row.get("start_s"), row.get("end_s")): row.get("hints") or []
        for row in hint_rows
        if isinstance(row, dict)
    }
    times = np.asarray(mix_loudness.get("times") or [], dtype=float)
    loudness = np.asarray(mix_loudness.get("loudness") or [], dtype=float)
    if not times.size or times.size != loudness.size:
        LOGGER.warning("Invalid mix loudness arrays for %s", song_path.name)
        return None

    low_energy = float(np.percentile(loudness, 35))
    high_energy = float(np.percentile(loudness, 70))
    beat_energy: list[dict[str, Any]] = []
    for index, beat in enumerate(beats):
        start_s = float(beat.get("time", 0.0))
        end_s = float(beats[index + 1].get("time", times[-1])) if index + 1 < len(beats) else float(times[-1])
        values = loudness[_window_mask(times, start_s, end_s)]
        if values.size:
            beat_energy.append(
                {
                    "time": start_s,
                    "bar": beat.get("bar"),
                    "beat": beat.get("beat"),
                    "energy": float(np.mean(values)),
                    "delta": float(np.mean(values) - np.median(loudness)),
                    "chord": beat.get("chord"),
                }
            )

    onset_times = np.asarray((mix_rhythm.get("onsets") or {}).get("times") or [], dtype=float)
    global_semantics = _model_tags(song_path)
    global_stem_accents = summarize_stem_accents(stem_profiles, 0.0, float(times[-1]), max_per_part=8)
    global_stem_dips = summarize_stem_dips(stem_profiles, 0.0, float(times[-1]), max_per_part=8)
    global_low_windows = merge_low_windows(global_stem_dips, max_windows=8)
    section_rows: list[dict[str, Any]] = []
    for section in sections:
        start_s = float(section["start_s"])
        end_s = float(section["end_s"])
        values = loudness[_window_mask(times, start_s, end_s)]
        if not values.size:
            LOGGER.warning("No loudness samples inside section %s for %s", section["name"], song_path.name)
            continue
        section_beats = [row for row in beats if start_s <= float(row.get("time", -1.0)) <= end_s]
        section_hints = list(hints_by_section.get((section["name"], section["start_s"], section["end_s"]), []))
        section_parts = _part_strengths(meta_dir / "essentia", start_s, end_s)
        section_onsets = onset_times[(onset_times >= start_s) & (onset_times <= end_s)]
        section_beat_energy = [row["energy"] for row in beat_energy if start_s <= float(row["time"]) <= end_s]
        stem_accents = summarize_stem_accents(stem_profiles, start_s, end_s)
        stem_dips = summarize_stem_dips(stem_profiles, start_s, end_s)
        low_windows = merge_low_windows(stem_dips)
        phrases = []
        for phrase in _phrase_windows(section, section_beats, section_hints):
            phrase_values = loudness[_window_mask(times, phrase["start_s"], phrase["end_s"])]
            if phrase_values.size:
                phrases.append(
                    {
                        **phrase,
                        "shape": _shape_label(phrase_values),
                        "energy_mean": float(np.mean(phrase_values)),
                        "energy_peak": float(np.max(phrase_values)),
                    }
                )
        semantics = _model_tags(song_path, start_s, end_s) if end_s - start_s >= 6.0 else {"available": False, "model_id": MODEL_ID, "tags": []}
        chord_labels = [row.get("chord") for row in section_beats if row.get("chord")]
        top_parts = [item["part"] for item in section_parts[:2]]
        mean_energy = float(np.mean(values))
        section_rows.append(
            {
                "name": section["name"],
                "start_s": start_s,
                "end_s": end_s,
                "energy": {
                    "mean": mean_energy,
                    "peak": float(np.max(values)),
                    "floor": float(np.min(values)),
                    "dynamic_range": float(np.max(values) - np.min(values)),
                    "trend": _shape_label(values),
                    "level": _energy_label(mean_energy, low_energy, high_energy),
                    "volatility": float(np.std(values)),
                },
                "rhythm": {
                    "beat_count": len(section_beats),
                    "onset_density": float(section_onsets.size / max(end_s - start_s, 1.0)),
                    "beat_loudness_mean": float(np.mean(section_beat_energy)) if section_beat_energy else None,
                },
                "harmony": {
                    "unique_chords": sorted({label for label in chord_labels if label != "N"}),
                    "change_count": sum(1 for index in range(1, len(chord_labels)) if chord_labels[index] != chord_labels[index - 1]),
                },
                "dominant_parts": section_parts,
                "stem_accents": stem_accents,
                "stem_dips": stem_dips,
                "low_windows": low_windows,
                "events": section_hints,
                "phrases": phrases,
                "semantic_tags": semantics,
                "summary": ", ".join(part for part in [section["name"], _energy_label(mean_energy, low_energy, high_energy), _shape_label(values), "/".join(top_parts) if top_parts else None] if part),
            }
        )

    payload = {
        "song_name": song_name(song_path),
        "source_song_path": str(song_path),
        "availability": {
            "beats": bool(beats),
            "sections": bool(sections),
            "hints": bool(hint_rows),
            "global_semantics": bool(global_semantics.get("available")),
        },
        "global": {
            "duration_s": float(mix_loudness.get("duration", times[-1])),
            "bpm": float(info_payload.get("bpm") or ((mix_rhythm.get("rhythm") or {}).get("bpm") or 0.0)),
            "analysis_bpm": float(((mix_rhythm.get("rhythm") or {}).get("bpm") or 0.0)),
            "key": {
                "canonical": info_payload.get("song_key"),
                "detected": mix_rhythm.get("key") or {},
            },
            "energy": {
                "mean": float(np.mean(loudness)),
                "peak": float(np.max(loudness)),
                "floor": float(np.min(loudness)),
                "dynamic_range": float(np.max(loudness) - np.min(loudness)),
                "volatility": float(np.std(loudness)),
            },
            "beat_energy": beat_energy,
            "peak_windows": [row for row in beat_energy if row["energy"] >= high_energy][:24],
            "stem_accents": global_stem_accents,
            "stem_dips": global_stem_dips,
            "low_windows": global_low_windows,
            "semantic_tags": global_semantics,
        },
        "sections": section_rows,
    }
    features_path = meta_dir / "features.json"
    _dump_json(features_path, payload)

    info_payload.setdefault("artifacts", {})["features_file"] = str(features_path)
    info_payload["feature_summary"] = {
        "section_count": len(section_rows),
        "peak_window_count": len(payload["global"]["peak_windows"]),
        "global_semantic_tags": [row["label"] for row in global_semantics.get("tags", [])],
    }
    _dump_json(info_path, info_payload)
    return features_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Find song features for light-show generation")
    parser.add_argument("song_path", type=str, help="Path to the source song file")
    parser.add_argument("--meta-path", type=str, default=META_PATH, help="Path to the analyzer meta root")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    output_path = find_song_features(args.song_path, meta_path=args.meta_path)
    if output_path is None:
        print(f"Could not generate features for {Path(args.song_path).stem}")
        return 1
    print(f"Generated song features: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())