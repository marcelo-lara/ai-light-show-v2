from __future__ import annotations


def build_song_context(manager) -> str:
    song = getattr(manager.state_manager, "current_song", None)
    if not song:
        return "Current song: unavailable"

    meta = getattr(song, "meta", None)
    song_name = str(getattr(meta, "song_name", None) or getattr(song, "song_id", "unknown"))
    bpm = getattr(meta, "bpm", None)
    duration = getattr(meta, "duration", None)
    song_key = str(getattr(meta, "song_key", None) or "unknown")

    bpm_text = _format_number(bpm, suffix=" BPM")
    duration_text = _format_number(duration, suffix=" seconds")

    return "\n".join(
        [
            "Current song context:",
            f"- Song name: {song_name}",
            f"- BPM: {bpm_text}",
            f"- Duration: {duration_text}",
            f"- Song key: {song_key}",
        ]
    )


def build_fixture_context(manager) -> str:
    fixtures = list(getattr(manager.state_manager, "fixtures", []) or [])
    if not fixtures:
        return "Available fixtures: unavailable"

    lines = ["Available fixtures in this show config:"]
    for fixture in fixtures:
        fixture_id = str(getattr(fixture, "id", "unknown"))
        fixture_name = str(getattr(fixture, "name", fixture_id))
        fixture_type = str(getattr(fixture, "type", "unknown"))
        effects = getattr(fixture, "effects", None) or []
        effects_text = ", ".join(str(effect) for effect in effects) if effects else "none"
        lines.append(
            f"- {fixture_id}: {fixture_name} [{fixture_type}] effects: {effects_text}"
        )

    return "\n".join(lines)


def _format_number(value, suffix: str) -> str:
    if value is None:
        return f"unknown{suffix}"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return f"unknown{suffix}"
    return f"{number:g}{suffix}"