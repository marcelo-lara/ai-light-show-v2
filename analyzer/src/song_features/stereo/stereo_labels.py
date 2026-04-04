from __future__ import annotations

from .stereo_tags import normalize_tags


def event_tags(source: str, group: list[dict[str, float | str]], left_focus: str, right_focus: str, corr: float, signed_balance: float) -> list[str]:
    left_transient = sum(float(window["left_transient"]) for window in group) / len(group)
    right_transient = sum(float(window["right_transient"]) for window in group) / len(group)
    decay = sum(float(window["decay"]) for window in group) / len(group)
    low_balance = sum(float(window["low_balance"]) for window in group) / len(group)
    mid_balance = sum(float(window["mid_balance"]) for window in group) / len(group)
    high_balance = sum(float(window["high_balance"]) for window in group) / len(group)
    tags: list[str] = []
    dominant_side = _dominant_side(signed_balance)
    if dominant_side == "left":
        tags.extend(_side_tags("left", source, left_focus, left_transient, decay, low_balance, mid_balance, high_balance))
        if _supports_secondary_tag(source, right_focus, right_transient, decay, low_balance, mid_balance, high_balance):
            tags.extend(_side_tags("right", source, right_focus, right_transient, decay, low_balance, mid_balance, high_balance, secondary=True))
    elif dominant_side == "right":
        tags.extend(_side_tags("right", source, right_focus, right_transient, decay, low_balance, mid_balance, high_balance))
        if _supports_secondary_tag(source, left_focus, left_transient, decay, low_balance, mid_balance, high_balance):
            tags.extend(_side_tags("left", source, left_focus, left_transient, decay, low_balance, mid_balance, high_balance, secondary=True))
    else:
        tags.extend(_contrast_tags(source, left_focus, right_focus, left_transient, right_transient, decay, low_balance, mid_balance, high_balance))
    if corr < -0.35 or (dominant_side == "contrast" and corr < 0.4):
        tags.append("split_texture")
    if abs(signed_balance) < 0.08 and corr > 0.9:
        tags.append("centered")
    return normalize_tags(tags)


def event_focus(tags: list[str], left_focus: str, right_focus: str) -> str:
    if any(tag.startswith("low_end") for tag in tags):
        return "low"
    if any(tag.startswith("attack") or tag.startswith("percussion") for tag in tags):
        return "high"
    if left_focus == right_focus:
        return left_focus
    return "broad"


def level(value: float, medium: float, high: float) -> str:
    if value >= high:
        return "high"
    if value >= medium:
        return "medium"
    return "low"


def _side_tags(
    side: str,
    source: str,
    focus: str,
    transient: float,
    decay: float,
    low_balance: float,
    mid_balance: float,
    high_balance: float,
    secondary: bool = False,
) -> list[str]:
    suffix = "left" if side == "left" else "right"
    tags: list[str] = []
    side_sign = 1.0 if side == "left" else -1.0
    if source == "bass" or (source != "drums" and (focus == "low" or low_balance * side_sign >= 0.04)):
        tags.append(f"low_end_{suffix}")
    if source == "drums" and not secondary:
        tags.append(f"percussion_{suffix}")
    elif (high_balance * side_sign >= 0.12 or transient >= (1.0 if secondary else 0.8)) and focus in {"mid", "high", "broad"}:
        tags.append(f"attack_{suffix}")
    if source != "drums" and (decay >= (0.01 if secondary else 0.004) or mid_balance * side_sign >= 0.05) and focus in {"mid", "high", "broad"}:
        tags.append(f"echo_{suffix}")
    if not tags and focus in {"mid", "high", "broad"} and not secondary:
        tags.append(f"ambience_{suffix}")
    return tags


def _contrast_tags(
    source: str,
    left_focus: str,
    right_focus: str,
    left_transient: float,
    right_transient: float,
    decay: float,
    low_balance: float,
    mid_balance: float,
    high_balance: float,
) -> list[str]:
    tags: list[str] = []
    if low_balance <= -0.04:
        tags.append("low_end_right")
    elif low_balance >= 0.04:
        tags.append("low_end_left")
    if source == "drums":
        side = "left" if left_transient >= right_transient else "right"
        tags.append(f"percussion_{side}")
    else:
        primary = "left" if left_transient >= right_transient else "right"
        secondary = "right" if primary == "left" else "left"
        primary_focus = left_focus if primary == "left" else right_focus
        secondary_focus = right_focus if primary == "left" else left_focus
        primary_transient = left_transient if primary == "left" else right_transient
        tags.extend(_side_tags(primary, source, primary_focus, primary_transient, decay, low_balance, mid_balance, high_balance))
        if source != "bass":
            tags.extend(_side_tags(secondary, source, secondary_focus, 0.0, decay, low_balance, mid_balance, high_balance, secondary=True))
    return tags


def _supports_secondary_tag(source: str, focus: str, transient: float, decay: float, low_balance: float, mid_balance: float, high_balance: float) -> bool:
    if source == "bass":
        return False
    if abs(low_balance) >= 0.04 or abs(mid_balance) >= 0.05 or abs(high_balance) >= 0.12:
        return True
    if decay >= 0.004:
        return True
    return transient >= 0.9 and focus in {"mid", "high", "broad"}


def _dominant_side(signed_balance: float) -> str:
    if signed_balance >= 0.06:
        return "left"
    if signed_balance <= -0.06:
        return "right"
    return "contrast"