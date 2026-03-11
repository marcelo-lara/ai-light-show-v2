from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def _parse_hex(value: str, *, require_hash: bool) -> Optional[Tuple[int, int, int]]:
    raw = str(value or "").strip()
    if require_hash and not raw.startswith("#"):
        return None

    if raw.startswith("#"):
        raw = raw[1:]

    if len(raw) != 6:
        return None

    try:
        red = int(raw[0:2], 16)
        green = int(raw[2:4], 16)
        blue = int(raw[4:6], 16)
        return red, green, blue
    except ValueError:
        return None


def rgb_to_hex(red: int, green: int, blue: int) -> str:
    r = max(0, min(255, int(red)))
    g = max(0, min(255, int(green)))
    b = max(0, min(255, int(blue)))
    return f"#{r:02X}{g:02X}{b:02X}"


def resolve_rgb_value(value: Any, mapping: Optional[Dict[str, Any]]) -> Optional[Tuple[int, int, int, str]]:
    token = str(value or "").strip()
    parsed_hex = _parse_hex(token, require_hash=True)
    if parsed_hex:
        return parsed_hex[0], parsed_hex[1], parsed_hex[2], rgb_to_hex(*parsed_hex)

    if not isinstance(mapping, dict):
        return None

    token_lc = token.lower()
    for name, mapped in mapping.items():
        if str(name).strip().lower() != token_lc:
            continue
        parsed_mapped = _parse_hex(str(mapped), require_hash=False)
        if not parsed_mapped:
            return None
        return parsed_mapped[0], parsed_mapped[1], parsed_mapped[2], rgb_to_hex(*parsed_mapped)

    return None