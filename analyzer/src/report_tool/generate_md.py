from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from src.storage.song_meta import lighting_score_path, music_feature_layers_path, song_name

META_PATH = os.environ.get("META_PATH", "/app/meta")


def _time(value: object) -> str:
    if isinstance(value, (int, float)):
        numeric = float(value)
    elif isinstance(value, str):
        numeric = float(value)
    else:
        numeric = 0.0
    return f"{numeric:.2f}"


def _load_ir(song_path: str | Path, meta_path: str | Path) -> dict[str, object] | None:
    path = music_feature_layers_path(song_path, meta_path)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _metadata_lines(ir: dict[str, object]) -> list[str]:
    metadata = ir.get("metadata") if isinstance(ir.get("metadata"), dict) else {}
    duration_s = float(metadata.get("duration_s", 0.0) or 0.0)
    minutes = int(duration_s // 60)
    seconds = int(duration_s % 60)
    return [
        "## Metadata",
        f"- Song: {metadata.get('title', '')}",
        f"- Artist: {metadata.get('artist', '')}",
        f"- Duration: {minutes}:{seconds:02d}",
        f"- BPM: {float(metadata.get('bpm', 0.0) or 0.0):.3f}",
        f"- Time Signature: {metadata.get('time_signature', '4/4')}",
        f"- Key: {metadata.get('key', '')}",
        "",
    ]


def _energy_lines(ir: dict[str, object]) -> list[str]:
    energy = ir.get("energy_profile") if isinstance(ir.get("energy_profile"), dict) else {}
    return [
        "## Energy Profile",
        f"- Loudness Mean: {float(energy.get('loudness_mean', 0.0) or 0.0):.3f}",
        f"- Loudness Peak: {float(energy.get('loudness_peak', 0.0) or 0.0):.3f}",
        f"- Loudness P90: {float(energy.get('loudness_percentile_90', 0.0) or 0.0):.3f}",
        f"- Dynamic Range: {float(energy.get('dynamic_range', 0.0) or 0.0):.3f}",
        f"- Transient Density: {float(energy.get('transient_density', 0.0) or 0.0):.3f}",
        f"- Energy Trend: {energy.get('energy_trend', 'unknown')}",
        f"- Brightness Trend: {energy.get('brightness_trend', 'unknown')}",
        f"- Centroid Mean: {float(energy.get('centroid_mean', 0.0) or 0.0):.3f}",
        f"- Centroid Peak: {float(energy.get('centroid_peak', 0.0) or 0.0):.3f}",
        f"- Onset Count: {int(energy.get('onset_count', 0) or 0)}",
        f"- Onset Density/Minute: {float(energy.get('onset_density_per_minute', 0.0) or 0.0):.3f}",
        f"- Flux Mean: {float(energy.get('flux_mean', 0.0) or 0.0):.3f}",
        f"- Flux Peak: {float(energy.get('flux_peak', 0.0) or 0.0):.3f}",
        f"- Brightness Summary: {energy.get('centroid_summary', '')}",
        f"- Flux Summary: {energy.get('flux_summary', '')}",
        "",
    ]


def _structure_lines(ir: dict[str, object]) -> list[str]:
    sections = (((ir.get("timeline") or {}).get("sections") or []) if isinstance(ir.get("timeline"), dict) else [])
    cards = ir.get("section_cards") if isinstance(ir.get("section_cards"), list) else []
    card_map = {str(card.get("section_name") or ""): card for card in cards if isinstance(card, dict)}
    lines = ["## Structure", "| Section | Time Range | Music |", "|---|---|---|"]
    for section in sections:
        if not isinstance(section, dict):
            continue
        name = str(section.get("name") or section.get("section_name") or "")
        card = card_map.get(name, {})
        lines.append(f"| {name} | {_time(section.get('start_s', 0.0))}-{_time(section.get('end_s', 0.0))} | {card.get('music_description', 'No summary available.')} |")
    lines.append("")
    return lines


def _section_plan_lines(ir: dict[str, object]) -> list[str]:
    cards = ir.get("section_cards") if isinstance(ir.get("section_cards"), list) else []
    lines = ["## Section Plan", ""]
    for card in cards:
        if not isinstance(card, dict):
            continue
        lines.append(f"### {card.get('section_name', '')} [{_time(card.get('start_s', 0.0))}-{_time(card.get('end_s', 0.0))}]")
        lines.append("")
        lines.append(f"Music: {card.get('music_description', 'No summary available.')}")
        energy_description = str(card.get("energy_description") or "")
        if energy_description:
            lines.append(f"Energy: {energy_description}")
        energy_profile = card.get("energy_profile") if isinstance(card.get("energy_profile"), dict) else {}
        if energy_profile:
            lines.append(
                "Energy Metrics: "
                f"level {energy_profile.get('level', 'unknown')}, "
                f"trend {energy_profile.get('trend', 'unknown')}, "
                f"loudness peak {float(energy_profile.get('loudness_peak', 0.0) or 0.0):.3f}, "
                f"centroid mean {float(energy_profile.get('centroid_mean', 0.0) or 0.0):.3f}, "
                f"flux mean {float(energy_profile.get('flux_mean', 0.0) or 0.0):.3f}"
            )
        implications = card.get("visual_implications") if isinstance(card.get("visual_implications"), list) else []
        if implications:
            lines.append(f"Visual Implications: {', '.join(str(item) for item in implications)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def generate_md_file(song_path: str | Path, meta_path: str | Path = META_PATH) -> Path | None:
    ir = _load_ir(song_path, meta_path)
    if not ir:
        return None
    lines = [f"# {song_name(song_path)} - Lighting Score", "", "## Musical Features", ""]
    lines.extend(_metadata_lines(ir))
    lines.extend(_energy_lines(ir))
    lines.extend(_structure_lines(ir))
    structure_summary = str(ir.get("structure_summary") or "")
    if structure_summary:
        lines.append("## Structure Summary")
        lines.append(structure_summary)
        lines.append("")
    mapping_rules = ir.get("mapping_rules") if isinstance(ir.get("mapping_rules"), list) else []
    if mapping_rules:
        lines.append("## Mapping Rules")
        lines.extend(f"- {rule}" for rule in mapping_rules)
        lines.append("")
    lines.append(_section_plan_lines(ir).rstrip())
    output_path = lighting_score_path(song_path, meta_path)
    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate lighting score markdown from merged analyzer IR")
    parser.add_argument("song_path", type=str, help="Path to the source song file")
    parser.add_argument("--meta-path", type=str, default=META_PATH, help="Path to the analyzer meta root")
    args = parser.parse_args()
    output_path = generate_md_file(args.song_path, meta_path=args.meta_path)
    if output_path is None:
        print(f"No merged music feature layers found for {Path(args.song_path).stem}")
        return 1
    print(f"Generated lighting score file: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())