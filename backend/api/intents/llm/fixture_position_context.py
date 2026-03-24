from __future__ import annotations

from typing import Any, Dict, List


def build_fixture_positions_payload(manager) -> Dict[str, Any]:
    fixtures = list(getattr(manager.state_manager, "fixtures", []) or [])
    items = [_fixture_position_payload(fixture) for fixture in fixtures]
    items.sort(key=lambda item: item["id"])
    answer = "Available fixture positions: " + ", ".join(item["id"] for item in items) + "." if items else "No fixtures are available."
    return {"fixtures": items, "answer": answer}


def _fixture_position_payload(fixture) -> Dict[str, Any]:
    location = dict(getattr(fixture, "location", {}) or {})
    x = _to_float(location.get("x"))
    y = _to_float(location.get("y"))
    z = _to_float(location.get("z"))
    selector_terms = sorted({
        *_name_tokens(getattr(fixture, "id", "")),
        *_name_tokens(getattr(fixture, "name", "")),
        *_name_tokens(getattr(fixture, "type", "")),
        _axis_label(x, "left", "right", "center"),
        _axis_label(y, "back", "front", "mid"),
        _axis_label(z, "floor", "ceiling", "mid"),
    })
    return {
        "id": str(getattr(fixture, "id", "")),
        "name": str(getattr(fixture, "name", "")),
        "type": str(getattr(fixture, "type", "")),
        "location": {"x": x, "y": y, "z": z},
        "position_labels": {
            "x": _axis_label(x, "left", "right", "center"),
            "y": _axis_label(y, "back", "front", "mid"),
            "z": _axis_label(z, "floor", "ceiling", "mid"),
        },
        "selector_terms": selector_terms,
    }


def _axis_label(value: float, low: str, high: str, middle: str) -> str:
    if value <= 0.34:
        return low
    if value >= 0.66:
        return high
    return middle


def _name_tokens(value: Any) -> List[str]:
    normalized = str(value or "").strip().lower().replace("-", "_").replace("(", " ").replace(")", " ")
    tokens = [token for token in normalized.replace("/", " ").replace("_", " ").split() if token]
    return tokens


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0