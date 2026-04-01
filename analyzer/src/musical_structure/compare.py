from __future__ import annotations

from pathlib import Path

from .io import load_beats, load_sections


def compare_beats(expected_path: Path, actual_path: Path) -> dict[str, float | int | bool]:
    expected = load_beats(expected_path.parent.name, expected_path.parent.parent, expected_path.name)
    actual = load_beats(actual_path.parent.name, actual_path.parent.parent, actual_path.name)
    comparable = max(len(expected), len(actual), 1)
    mismatches = abs(len(expected) - len(actual))
    for expected_row, actual_row in zip(expected, actual):
        if (expected_row.get("chord") or "N") != (actual_row.get("chord") or "N"):
            mismatches += 1
    error_rate = mismatches / comparable
    return {"comparable": comparable, "mismatches": mismatches, "error_rate": error_rate, "ok": error_rate <= 0.10}


def compare_sections(expected_path: Path, actual_path: Path) -> dict[str, float | bool]:
    expected = load_sections(expected_path.parent.name, expected_path.parent.parent, expected_path.name)
    actual = load_sections(actual_path.parent.name, actual_path.parent.parent, actual_path.name)
    total = sum(max(float(row.get("end", 0.0)) - float(row.get("start", 0.0)), 0.0) for row in expected) or 1.0
    matched = 0.0
    for expected_row in expected:
        expected_start = float(expected_row.get("start", 0.0))
        expected_end = float(expected_row.get("end", expected_start))
        expected_label = expected_row.get("label")
        for actual_row in actual:
            if actual_row.get("label") != expected_label:
                continue
            overlap_start = max(expected_start, float(actual_row.get("start", 0.0)))
            overlap_end = min(expected_end, float(actual_row.get("end", overlap_start)))
            matched += max(overlap_end - overlap_start, 0.0)
    error_rate = max(0.0, 1.0 - (matched / total))
    return {"matched_duration": round(matched, 3), "total_duration": round(total, 3), "error_rate": error_rate, "ok": error_rate <= 0.10}