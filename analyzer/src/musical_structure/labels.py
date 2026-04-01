from __future__ import annotations

import re

NO_CHORD = {"", "n", "nc", "none", "no chord", "no_chord"}
SECTION_LABELS = {
    "intro": "Intro",
    "verse": "Verse",
    "pre": "Pre-Chorus",
    "chorus": "Chorus",
    "bridge": "Bridge",
    "outro": "Outro",
    "instrumental": "Instrumental",
    "solo": "Instrumental",
    "drop": "Instrumental",
    "break": "Instrumental",
}
ROOT_ALIASES = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}


def normalize_chord_label(value: str | None) -> str | None:
    text = (value or "").strip().replace("♯", "#").replace("♭", "b")
    compact = re.sub(r"\s+", " ", text).lower()
    if compact in NO_CHORD:
        return "N"
    match = re.match(r"^([a-gA-G])([#b]?)(.*)$", text)
    if match is None:
        return None
    root = f"{match.group(1).upper()}{match.group(2)}"
    root = ROOT_ALIASES.get(root, root)
    quality = match.group(3).strip().lower().replace(" ", "")
    if quality in {"", "maj", "major"}:
        return root
    if quality.startswith(("m", "min", "minor")) and not quality.startswith("maj"):
        suffix = quality.replace("minor", "m").replace("min", "m")
        return f"{root}{suffix if suffix.startswith('m') else 'm'}"
    if quality.startswith("dim"):
        return f"{root}dim"
    if quality.startswith("aug"):
        return f"{root}aug"
    if quality.startswith("sus") or quality.startswith("7"):
        return f"{root}{quality}"
    return root


def bass_note_from_label(value: str | None) -> str | None:
    chord = normalize_chord_label(value)
    if chord in {None, "N"}:
        return None
    match = re.match(r"^([A-G][#]?)(.*)$", chord)
    return match.group(1) if match else None


def normalize_section_label(value: str | None) -> str | None:
    text = (value or "").strip().lower().replace("_", " ")
    if not text:
        return None
    for key, label in SECTION_LABELS.items():
        if key in text:
            return label
    return None