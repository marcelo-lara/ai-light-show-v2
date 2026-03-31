from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from src.song_meta import load_sections, song_meta_dir, song_name

META_PATH = os.environ.get("META_PATH", "/app/meta")


def _time(value: object) -> str:
    if isinstance(value, (int, float)):
        numeric = float(value)
    elif isinstance(value, str):
        numeric = float(value)
    else:
        numeric = 0.0
    return f"{numeric:.2f}"


def _relevant_part_names(parts: object, *, limit: int = 2) -> list[str]:
    if not isinstance(parts, list):
        return []
    filtered = [
        str(part.get("part"))
        for part in parts
        if isinstance(part, dict)
        and isinstance(part.get("part"), str)
        and part.get("part") != "mix"
        and float(part.get("share", 0.0) or 0.0) >= 0.08
    ]
    return filtered[:limit]


def _load_features(meta_dir: Path) -> dict[str, object] | None:
    path = meta_dir / "features.json"
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _render_feature_summary(features: dict[str, object]) -> list[str]:
    global_payload = features.get("global") if isinstance(features.get("global"), dict) else {}
    energy = global_payload.get("energy") if isinstance(global_payload, dict) else {}
    semantic_tags = global_payload.get("semantic_tags") if isinstance(global_payload, dict) else {}
    tags = semantic_tags.get("tags") if isinstance(semantic_tags, dict) else []
    raw_stem_accents = global_payload.get("stem_accents") if isinstance(global_payload, dict) else None
    stem_accents = raw_stem_accents if isinstance(raw_stem_accents, list) else []
    raw_low_windows = global_payload.get("low_windows") if isinstance(global_payload, dict) else None
    low_windows = raw_low_windows if isinstance(raw_low_windows, list) else []
    lines = ["## Feature Summary", ""]
    if isinstance(energy, dict):
        lines.append(
            f"Energy mean {energy.get('mean', 0.0):.3f}, peak {energy.get('peak', 0.0):.3f}, range {energy.get('dynamic_range', 0.0):.3f}."
        )
    if isinstance(tags, list) and tags:
        label_text = ", ".join(str(tag.get("label")) for tag in tags[:5] if isinstance(tag, dict) and tag.get("label"))
        if label_text:
            lines.append(f"Model tags: {label_text}.")
    if stem_accents:
        stem_lines = []
        for entry in stem_accents[:4]:
            if not isinstance(entry, dict):
                continue
            accents = entry.get("accents") if isinstance(entry.get("accents"), list) else []
            if not accents:
                continue
            times = ", ".join(_time(accent.get("time", 0.0)) for accent in accents[:4] if isinstance(accent, dict))
            if times:
                stem_lines.append(f"{entry.get('part')}: {times}")
        if stem_lines:
            lines.append(f"Accents: {'; '.join(stem_lines)}.")
    if low_windows:
        windows = ", ".join(
            f"{_time(window.get('start_s', 0.0))}-{_time(window.get('end_s', 0.0))} ({', '.join(window.get('parts') or [])})"
            for window in low_windows[:4]
            if isinstance(window, dict) and isinstance(window.get("parts"), list)
        )
        if windows:
            lines.append(f"Dips: {windows}.")
    lines.append("")
    return lines


def _render_section_feature(section: dict[str, object], features: dict[str, object] | None) -> list[str]:
    if not features:
        return []
    raw_sections = features.get("sections")
    feature_sections = raw_sections if isinstance(raw_sections, list) else []
    match = next(
        (
            row for row in feature_sections
            if isinstance(row, dict) and row.get("name") == section["name"] and row.get("start_s") == section["start_s"]
        ),
        None,
    )
    if not isinstance(match, dict):
        return []
    energy = match.get("energy") if isinstance(match.get("energy"), dict) else {}
    raw_parts = match.get("dominant_parts")
    dominant_parts = raw_parts if isinstance(raw_parts, list) else []
    raw_phrases = match.get("phrases")
    phrases = raw_phrases if isinstance(raw_phrases, list) else []
    raw_stem_accents = match.get("stem_accents")
    stem_accents = raw_stem_accents if isinstance(raw_stem_accents, list) else []
    raw_low_windows = match.get("low_windows")
    low_windows = raw_low_windows if isinstance(raw_low_windows, list) else []
    top_parts = ", ".join(_relevant_part_names(dominant_parts))
    lines: list[str] = []
    if isinstance(match.get("summary"), str) and match.get("summary"):
        lines.append(str(match.get("summary")))
    if isinstance(energy, dict):
        lines.append(
            f"Energy: {energy.get('level', 'unknown')} with {energy.get('trend', 'unknown')} trend, peak {energy.get('peak', 0.0):.3f}."
        )
    if top_parts:
        lines.append(f"Dominant parts: {top_parts}.")
    if phrases:
        phrase_text = ", ".join(
            f"{_time(phrase.get('start_s', 0.0))}-{_time(phrase.get('end_s', 0.0))} {phrase.get('shape', 'unknown')}"
            for phrase in phrases[:3]
            if isinstance(phrase, dict)
        )
        if phrase_text:
            lines.append(f"Phrases: {phrase_text}.")
    if stem_accents:
        stem_lines = []
        for entry in stem_accents[:4]:
            if not isinstance(entry, dict):
                continue
            accents = entry.get("accents") if isinstance(entry.get("accents"), list) else []
            if not accents:
                continue
            times = ", ".join(_time(accent.get("time", 0.0)) for accent in accents[:6] if isinstance(accent, dict))
            if times:
                stem_lines.append(f"{entry.get('part')} at {times}")
        if stem_lines:
            lines.append(f"Accents: {'; '.join(stem_lines)}.")
    if low_windows:
        windows = ", ".join(
            f"{_time(window.get('start_s', 0.0))}-{_time(window.get('end_s', 0.0))} ({', '.join(window.get('parts') or [])})"
            for window in low_windows[:4]
            if isinstance(window, dict) and isinstance(window.get("parts"), list)
        )
        if windows:
            lines.append(f"Dips: {windows}.")
    return [line for line in lines if line]


def _render_markdown(song: str, sections: list[dict[str, object]], features: dict[str, object] | None) -> str:
    lines = [f"# {song} - Light Show", ""]
    if features:
        lines.extend(_render_feature_summary(features))
    for section in sections:
        lines.append(f"## {section['name']} [{_time(section['start_s'])}-{_time(section['end_s'])}]")
        lines.append("")
        lines.extend(_render_section_feature(section, features))
        if lines[-1] != "":
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def generate_md_file(song_path: str | Path, meta_path: str | Path = META_PATH) -> Path | None:
    meta_dir = song_meta_dir(song_path, meta_path)
    sections = load_sections(meta_dir)
    if not sections:
        return None
    features = _load_features(meta_dir)
    output_path = meta_dir / f"{song_name(song_path)}.md"
    output_path.write_text(_render_markdown(song_name(song_path), sections, features), encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate song markdown from analyzer sections")
    parser.add_argument("song_path", type=str, help="Path to the source song file")
    parser.add_argument("--meta-path", type=str, default=META_PATH, help="Path to the analyzer meta root")
    args = parser.parse_args()

    output_path = generate_md_file(args.song_path, meta_path=args.meta_path)
    if output_path is None:
        print(f"No sections metadata found for {Path(args.song_path).stem}")
        return 1
    print(f"Generated markdown file: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())