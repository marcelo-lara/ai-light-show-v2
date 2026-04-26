from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

from .analysis_contract import DominantPart, LowWindow, SectionAnalysis, SectionEvent, SongAnalysis, StemAccent, StemDip
from .analysis_files import attach_section_positions, load_json, normalize_sections, resolve_meta_path

TModel = TypeVar("TModel", StemAccent, StemDip)


def resolve_analysis_artifact_paths(song) -> dict[str, Path]:
    meta_root = Path(song.base_dir)
    artifacts = getattr(song.meta, "artifacts", {}) or {}
    return {
        "features_file": resolve_meta_path(
            meta_root,
            str(artifacts.get("features_file") or artifacts.get("energy_layer") or artifacts.get("energy_features") or ""),
            song.song_id,
            "features.json",
        ),
        "hints_file": resolve_meta_path(
            meta_root,
            str(artifacts.get("hints_file") or artifacts.get("music_feature_layers") or artifacts.get("lighting_events") or ""),
            song.song_id,
            "hints.json",
        ),
    }


def collect_missing_analysis_artifacts(song) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    for artifact, path in resolve_analysis_artifact_paths(song).items():
        if path.exists():
            continue
        missing.append({"artifact": artifact, "path": str(path)})
    return missing


def build_song_analysis(song) -> SongAnalysis:
    artifact_paths = resolve_analysis_artifact_paths(song)
    features_path = artifact_paths["features_file"]
    hints_path = artifact_paths["hints_file"]
    features_payload = load_json(features_path)
    hints_payload = load_json(hints_path)
    beats = list(getattr(getattr(song, "beats", None), "beats", []) or [])
    sections = attach_section_positions(normalize_sections(getattr(getattr(song, "sections", None), "sections", []) or []), beats)
    feature_sections = build_feature_sections(features_payload)
    hint_sections = build_hint_sections(hints_payload, sections)
    normalized_sections = [build_section(section, feature_sections, hint_sections) for section in sections]
    return SongAnalysis(
        song_id=song.song_id,
        bpm=float(getattr(song.meta, "bpm", 0.0) or 0.0),
        duration_s=float(getattr(song.meta, "duration", 0.0) or 0.0),
        beats_available=bool(beats),
        sections_available=bool(sections),
        features_available=bool(feature_sections),
        hints_available=bool(hint_sections),
        available_parts=collect_parts(normalized_sections),
        global_energy=dict((features_payload or {}).get("global_energy") or ((features_payload or {}).get("global") or {}).get("energy") or {}),
        beats=beats,
        sections=normalized_sections,
    )


def build_section(section: dict[str, Any], feature_sections: dict[tuple[float, float], dict[str, Any]], hint_sections: dict[tuple[float, float], dict[str, Any]]) -> SectionAnalysis:
    feature = lookup_section_payload(feature_sections, section)
    hints = lookup_section_payload(hint_sections, section)
    return SectionAnalysis(
        **section,
        energy=dict(feature.get("energy") or {}),
        rhythm=dict(feature.get("rhythm") or {}),
        harmony=dict(feature.get("harmony") or {}),
        dominant_parts=[DominantPart(**item) for item in feature.get("dominant_parts") or [] if isinstance(item, dict) and item.get("part")],
        events=[SectionEvent(**normalize_event(item)) for item in (feature.get("events") or hints.get("events") or hints.get("hints") or []) if isinstance(item, dict) and item.get("kind")],
        stem_accents=build_part_map(feature.get("stem_accents") or [], "accents", StemAccent),
        stem_dips=build_part_map(feature.get("stem_dips") or [], "dips", StemDip),
        low_windows=[LowWindow(**item) for item in feature.get("low_windows") or [] if isinstance(item, dict)],
    )


def section_key(section: dict[str, Any]) -> tuple[float, float]:
    return (round(float(section.get("start_s", 0.0) or 0.0), 3), round(float(section.get("end_s", 0.0) or 0.0), 3))


def index_sections(rows: list[dict[str, Any]]) -> dict[tuple[float, float], dict[str, Any]]:
    indexed: dict[tuple[float, float], dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        indexed[section_key(row)] = row
    return indexed


def lookup_section_payload(indexed: dict[tuple[float, float], dict[str, Any]], section: dict[str, Any], tolerance_s: float = 0.05) -> dict[str, Any]:
    key = section_key(section)
    exact = indexed.get(key)
    if exact is not None:
        return exact
    start_s, end_s = key
    for (candidate_start, candidate_end), payload in indexed.items():
        if abs(candidate_start - start_s) <= tolerance_s and abs(candidate_end - end_s) <= tolerance_s:
            return payload
    return {}


def build_feature_sections(payload: Any) -> dict[tuple[float, float], dict[str, Any]]:
    if not isinstance(payload, dict):
        return {}
    if isinstance(payload.get("sections"), list):
        return index_sections(payload.get("sections") or [])
    if not isinstance(payload.get("section_energy"), list):
        return {}
    rows = []
    for row in payload.get("section_energy") or []:
        if not isinstance(row, dict):
            continue
        rows.append(
            {
                "start_s": row.get("start_s"),
                "end_s": row.get("end_s"),
                "energy": {
                    "level": row.get("level"),
                    "trend": row.get("trend"),
                    "mean": row.get("mean"),
                    "peak": row.get("peak"),
                    "transient_density": row.get("transient_density"),
                },
            }
        )
    return index_sections(rows)


def build_hint_sections(payload: Any, sections: list[dict[str, Any]]) -> dict[tuple[float, float], dict[str, Any]]:
    if isinstance(payload, list):
        return index_sections(payload)
    if not isinstance(payload, dict):
        return {}
    if isinstance(payload.get("cue_anchors"), list):
        return build_lighting_event_hint_sections(payload, sections)
    timeline = payload.get("timeline")
    if isinstance(timeline, dict):
        return build_music_feature_layer_hint_sections(timeline, sections)
    return {}


def build_lighting_event_hint_sections(payload: dict[str, Any], sections: list[dict[str, Any]]) -> dict[tuple[float, float], dict[str, Any]]:
    indexed: dict[tuple[float, float], dict[str, Any]] = {section_key(section): {"events": []} for section in sections}
    for anchor in payload.get("cue_anchors") or []:
        if not isinstance(anchor, dict):
            continue
        time_s = float(anchor.get("time_s", 0.0) or 0.0)
        anchor_type = str(anchor.get("anchor_type") or "")
        if not anchor_type.startswith("accent"):
            continue
        for section in sections:
            start_s = float(section.get("start_s", 0.0) or 0.0)
            end_s = float(section.get("end_s", start_s) or start_s)
            if start_s <= time_s < end_s:
                indexed[section_key(section)]["events"].append(
                    {
                        "kind": anchor_type,
                        "time_s": time_s,
                        "dominant_part": "mix",
                        "parts": [],
                    }
                )
                break
    return indexed


def build_music_feature_layer_hint_sections(timeline: dict[str, Any], sections: list[dict[str, Any]]) -> dict[tuple[float, float], dict[str, Any]]:
    indexed: dict[tuple[float, float], dict[str, Any]] = {section_key(section): {"events": []} for section in sections}

    for phrase in timeline.get("phrases") or []:
        if not isinstance(phrase, dict):
            continue
        event = {
            "kind": "phrase_window",
            "dominant_part": "mix",
            "parts": [],
            "start_s": float(phrase.get("start_s", 0.0) or 0.0),
            "end_s": float(phrase.get("end_s", 0.0) or 0.0),
        }
        append_section_event(indexed, sections, event)

    for accent in timeline.get("accent_windows") or []:
        if not isinstance(accent, dict):
            continue
        event = {
            "kind": f"accent_{str(accent.get('kind') or 'hit')}",
            "dominant_part": "mix",
            "parts": [],
            "time_s": float(accent.get("time_s", 0.0) or 0.0),
            "strength": float(accent.get("intensity", 0.0) or 0.0),
        }
        append_section_event(indexed, sections, event)

    return indexed


def append_section_event(indexed: dict[tuple[float, float], dict[str, Any]], sections: list[dict[str, Any]], event: dict[str, Any]) -> None:
    time_s = event.get("time_s")
    start_s = event.get("start_s")
    end_s = event.get("end_s")
    for section in sections:
        section_start = float(section.get("start_s", 0.0) or 0.0)
        section_end = float(section.get("end_s", section_start) or section_start)
        if time_s is not None and section_start <= float(time_s) < section_end:
            indexed[section_key(section)]["events"].append(event)
            return
        if start_s is not None and end_s is not None and float(start_s) >= section_start and float(end_s) <= section_end:
            indexed[section_key(section)]["events"].append(event)
            return


def build_part_map(rows: list[dict[str, Any]], child_key: str, model: type[TModel]) -> dict[str, list[TModel]]:
    mapped: dict[str, list[TModel]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        part = str(row.get("part") or "").strip()
        if not part:
            continue
        mapped[part] = [model(**item) for item in row.get(child_key) or [] if isinstance(item, dict)]
    return mapped


def normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    payload = dict(event)
    payload["dominant_part"] = str(payload.get("dominant_part") or "mix")
    payload["parts"] = [str(part) for part in payload.get("parts") or []]
    return payload


def collect_parts(sections: list[SectionAnalysis]) -> list[str]:
    parts = {part.part for section in sections for part in section.dominant_parts}
    parts.update(part for section in sections for part in section.stem_accents.keys())
    parts.update(part for section in sections for part in section.stem_dips.keys())
    return sorted(part for part in parts if part)