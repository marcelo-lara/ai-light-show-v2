from __future__ import annotations

from typing import Any


def get_essentia_artifact_entry(artifacts: dict[str, Any] | None, part: str, feature: str) -> dict[str, Any] | None:
    essentia = (artifacts or {}).get("essentia") if isinstance(artifacts, dict) else None
    if not isinstance(essentia, dict):
        return None
    part_entry = essentia.get(part)
    if isinstance(part_entry, dict):
        feature_entry = part_entry.get(feature)
        if isinstance(feature_entry, dict):
            return feature_entry
    if part == "mix":
        feature_entry = essentia.get(feature)
        if isinstance(feature_entry, dict):
            return feature_entry
    flat_entry = essentia.get(f"{part}_{feature}" if part != "mix" else feature)
    return flat_entry if isinstance(flat_entry, dict) else None


def build_essentia_plot_descriptors(artifacts: dict[str, Any] | None) -> list[dict[str, str]]:
    essentia = (artifacts or {}).get("essentia") if isinstance(artifacts, dict) else None
    if not isinstance(essentia, dict):
        return []
    plots: list[dict[str, str]] = []

    def visit(node: dict[str, Any], prefix: list[str]) -> None:
        for key, value in node.items():
            if not isinstance(value, dict):
                continue
            if value.get("svg"):
                parts = prefix + [str(key)]
                artifact_id = parts[-1] if parts[:-1] == ["mix"] or not parts[:-1] else "_".join(parts)
                plots.append({"id": artifact_id, "title": artifact_id.replace("_", " ").title(), "svg": str(value["svg"])})
                continue
            visit(value, prefix + [str(key)])

    visit(essentia, [])
    return plots