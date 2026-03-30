from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar

from .analysis_contract import DominantPart, LowWindow, SectionAnalysis, SectionEvent, SongAnalysis, StemAccent, StemDip
from .analysis_files import attach_section_positions, load_json, normalize_sections, resolve_meta_path

TModel = TypeVar("TModel", StemAccent, StemDip)


def build_song_analysis(song) -> SongAnalysis:
    meta_root = Path(song.base_dir)
    artifacts = getattr(song.meta, "artifacts", {}) or {}
    features_path = resolve_meta_path(meta_root, str(artifacts.get("features_file") or ""), song.song_id, "features.json")
    hints_path = resolve_meta_path(meta_root, str(artifacts.get("hints_file") or ""), song.song_id, "hints.json")
    features_payload = load_json(features_path)
    hints_payload = load_json(hints_path)
    feature_sections = index_sections((features_payload or {}).get("sections") or [])
    hint_sections = index_sections(hints_payload or [])
    beats = list(getattr(getattr(song, "beats", None), "beats", []) or [])
    sections = attach_section_positions(normalize_sections(getattr(getattr(song, "sections", None), "sections", []) or []), beats)
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
        global_energy=dict(((features_payload or {}).get("global") or {}).get("energy") or {}),
        beats=beats,
        sections=normalized_sections,
    )


def build_section(section: dict[str, Any], feature_sections: dict[tuple[float, float], dict[str, Any]], hint_sections: dict[tuple[float, float], dict[str, Any]]) -> SectionAnalysis:
    key = section_key(section)
    feature = feature_sections.get(key) or {}
    hints = hint_sections.get(key) or {}
    return SectionAnalysis(
        **section,
        energy=dict(feature.get("energy") or {}),
        rhythm=dict(feature.get("rhythm") or {}),
        harmony=dict(feature.get("harmony") or {}),
        dominant_parts=[DominantPart(**item) for item in feature.get("dominant_parts") or [] if isinstance(item, dict) and item.get("part")],
        events=[SectionEvent(**normalize_event(item)) for item in (feature.get("events") or hints.get("hints") or []) if isinstance(item, dict) and item.get("kind")],
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