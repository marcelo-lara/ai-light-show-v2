from __future__ import annotations

from typing import Any, Dict, List


def build_song_context(manager) -> str:
    payload = build_song_context_payload(manager)
    if not payload.get("song_name"):
        return "Current song: unavailable"

    return "\n".join(
        [
            "Current song context:",
            f"- Song name: {payload['song_name']}",
            f"- BPM: {payload['bpm']}",
            f"- Duration: {payload['duration']}",
            f"- Song key: {payload['song_key']}",
        ]
    )


def build_fixture_context(manager) -> str:
    fixtures = build_fixture_inventory_payload(manager)
    if not fixtures:
        return "Available fixtures: unavailable"

    lines = ["Available fixtures in this show config:"]
    for fixture in fixtures:
        fixture_id = str(fixture.get("id", "unknown"))
        fixture_name = str(fixture.get("name", fixture_id))
        fixture_type = str(fixture.get("type", "unknown"))
        effects = fixture.get("supported_effects") or []
        effects_text = ", ".join(str(effect) for effect in effects) if effects else "none"
        lines.append(
            f"- {fixture_id}: {fixture_name} [{fixture_type}] effects: {effects_text}"
        )

    return "\n".join(lines)


def build_song_context_payload(manager) -> Dict[str, str]:
    song = getattr(manager.state_manager, "current_song", None)
    if not song:
        return {
            "song_name": "",
            "bpm": "unknown BPM",
            "duration": "unknown seconds",
            "song_key": "unknown",
            "song_id": "",
        }

    meta = getattr(song, "meta", None)
    song_name = str(getattr(meta, "song_name", None) or getattr(song, "song_id", "unknown"))
    return {
        "song_name": song_name,
        "song_id": str(getattr(song, "song_id", song_name)),
        "bpm": _format_number(getattr(meta, "bpm", None), suffix=" BPM"),
        "duration": _format_number(getattr(meta, "duration", None), suffix=" seconds"),
        "song_key": str(getattr(meta, "song_key", None) or "unknown"),
    }


def build_song_sections_payload(manager) -> Dict[str, Any]:
    song_context = build_song_context_payload(manager)
    song = getattr(manager.state_manager, "current_song", None)
    sections = getattr(getattr(song, "sections", None), "sections", None) or []
    normalized_sections: List[Dict[str, Any]] = []

    for section in sections:
        if not isinstance(section, dict):
            continue

        start_raw = section.get("start_s")
        if start_raw is None:
            start_raw = section.get("start")

        end_raw = section.get("end_s")
        if end_raw is None:
            end_raw = section.get("end")

        name_raw = section.get("name")
        if not name_raw:
            name_raw = section.get("label")

        normalized_sections.append(
            {
                "name": str(name_raw or ""),
                "start_s": float(start_raw or 0.0),
                "end_s": float(end_raw or 0.0),
            }
        )

    normalized_sections.sort(key=lambda item: item["start_s"])
    return {**song_context, "sections": normalized_sections}


def build_fixture_inventory_payload(manager) -> List[Dict[str, Any]]:
    fixtures = list(getattr(manager.state_manager, "fixtures", []) or [])
    return [_fixture_payload(manager, fixture) for fixture in fixtures]


def build_fixture_detail_payload(manager, fixture_id: str) -> Dict[str, Any] | None:
    fixtures = list(getattr(manager.state_manager, "fixtures", []) or [])
    fixture = next((item for item in fixtures if str(getattr(item, "id", "")) == fixture_id), None)
    if fixture is None:
        return None
    return _fixture_payload(manager, fixture, detailed=True)


def _fixture_payload(manager, fixture, *, detailed: bool = False) -> Dict[str, Any]:
    supported_effects_fn = getattr(manager.state_manager, "_fixture_supported_effects", None)
    if callable(supported_effects_fn):
        supported_effects = sorted(supported_effects_fn(fixture))
    else:
        supported_effects = sorted(str(effect) for effect in (getattr(fixture, "effects", None) or []))
    payload: Dict[str, Any] = {
        "id": str(getattr(fixture, "id", "unknown")),
        "name": str(getattr(fixture, "name", "unknown")),
        "type": str(getattr(fixture, "type", "unknown")),
        "supported_effects": supported_effects,
    }
    if detailed:
        payload["meta_channels"] = {key: value.model_dump() for key, value in fixture.meta_channels.items()}
        payload["mappings"] = fixture.mappings
    return payload


def _format_number(value, suffix: str) -> str:
    if value is None:
        return f"unknown{suffix}"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return f"unknown{suffix}"
    return f"{number:g}{suffix}"