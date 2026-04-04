from __future__ import annotations

from collections import Counter

from .stereo_labels import event_focus, event_tags, level


def build_notable_events(source: str, windows: list[dict[str, float | str]]) -> list[dict[str, object]]:
    if not windows:
        return []
    energy_threshold = sorted(float(window["energy"]) for window in windows)[max(len(windows) // 5 - 1, 0)]
    candidates = [window for window in windows if _is_notable(source, window, energy_threshold)]
    groups = _merge_candidates(candidates)
    events = [event for event in (_finalize_event(source, group) for group in groups) if event is not None]
    return _coalesce_events(source, events)


def _is_notable(source: str, window: dict[str, float | str], energy_threshold: float) -> bool:
    balance = abs(float(window["balance"]))
    corr = float(window["corr"])
    focus_contrast = window["left_focus"] != window["right_focus"]
    if source == "bass":
        return float(window["energy"]) >= energy_threshold * 0.6 and (balance >= 0.05 or corr <= 0.25)
    if source == "mix":
        return float(window["energy"]) >= energy_threshold * 0.75 and (balance >= 0.1 or corr <= -0.45 or focus_contrast)
    return float(window["energy"]) >= energy_threshold and (balance >= 0.18 or corr <= 0.55 or focus_contrast)


def _merge_candidates(candidates: list[dict[str, float | str]]) -> list[list[dict[str, float | str]]]:
    groups: list[list[dict[str, float | str]]] = []
    for window in candidates:
        if groups and _compatible(groups[-1][-1], window):
            groups[-1].append(window)
        else:
            groups.append([window])
    return [group for group in groups if len(group) >= 2 or float(group[0]["energy"]) >= 0.04]


def _compatible(left: dict[str, float | str], right: dict[str, float | str]) -> bool:
    gap = float(right["start_s"]) - float(left["end_s"])
    same_side = _dominant_side(left) == _dominant_side(right)
    similar_focus = left["left_focus"] == right["left_focus"] and left["right_focus"] == right["right_focus"]
    return gap <= 0.35 and (same_side or similar_focus)


def _finalize_event(source: str, group: list[dict[str, float | str]]) -> dict[str, object] | None:
    balance = sum(abs(float(window["balance"])) for window in group) / len(group)
    signed_balance = sum(float(window["balance"]) for window in group) / len(group)
    corr = sum(float(window["corr"]) for window in group) / len(group)
    if source == "bass" and abs(signed_balance) < 0.08:
        return None
    left_focus = Counter(str(window["left_focus"]) for window in group).most_common(1)[0][0]
    right_focus = Counter(str(window["right_focus"]) for window in group).most_common(1)[0][0]
    tags = event_tags(source, group, left_focus, right_focus, corr, signed_balance)
    if not tags:
        return None
    return {
        "start_s": float(group[0]["start_s"]),
        "end_s": float(group[-1]["end_s"]),
        "source": source,
        "dominant_side": _event_side(group, corr, signed_balance),
        "intensity": level(balance, 0.3, 0.5),
        "confidence": level(balance + max(0.0, 0.5 - corr), 0.45, 0.75),
        "frequency_focus": event_focus(tags, left_focus, right_focus),
        "tags": tags,
    }


def _dominant_side(window: dict[str, float | str]) -> str:
    balance = float(window["balance"])
    if balance >= 0.12:
        return "left"
    if balance <= -0.12:
        return "right"
    return "contrast"


def _event_side(group: list[dict[str, float | str]], corr: float, signed_balance: float) -> str:
    side = Counter(_dominant_side(window) for window in group).most_common(1)[0][0]
    if signed_balance >= 0.06:
        return "left"
    if signed_balance <= -0.06:
        return "right"
    return "contrast" if side == "contrast" or corr < 0.4 else side


def _coalesce_events(source: str, events: list[dict[str, object]]) -> list[dict[str, object]]:
    if not events:
        return []
    merged: list[dict[str, object]] = []
    for event in events:
        if merged and _mergeable(source, merged[-1], event):
            merged[-1] = _merge_event_pair(merged[-1], event)
        else:
            merged.append(dict(event))
    return merged


def _mergeable(source: str, left: dict[str, object], right: dict[str, object]) -> bool:
    gap = float(right["start_s"]) - float(left["end_s"])
    if gap > _gap_threshold(source):
        return False
    if left["dominant_side"] != right["dominant_side"]:
        return False
    left_tags = set(str(tag) for tag in left.get("tags", []))
    right_tags = set(str(tag) for tag in right.get("tags", []))
    if left_tags & right_tags:
        return True
    if source == "mix":
        return True
    return False


def _merge_event_pair(left: dict[str, object], right: dict[str, object]) -> dict[str, object]:
    tags = _merge_tags(list(left.get("tags", [])), list(right.get("tags", [])))
    return {
        "start_s": float(left["start_s"]),
        "end_s": float(right["end_s"]),
        "source": left["source"],
        "dominant_side": left["dominant_side"],
        "intensity": _max_level(str(left["intensity"]), str(right["intensity"])),
        "confidence": _max_level(str(left["confidence"]), str(right["confidence"])),
        "frequency_focus": _merged_focus(str(left["frequency_focus"]), str(right["frequency_focus"]), tags),
        "tags": tags,
    }


def _merge_tags(left: list[object], right: list[object]) -> list[str]:
    combined = [str(tag) for tag in left] + [str(tag) for tag in right]
    preferred = [
        "percussion_left",
        "percussion_right",
        "attack_left",
        "attack_right",
        "echo_left",
        "echo_right",
        "low_end_left",
        "low_end_right",
        "ambience_left",
        "ambience_right",
        "split_texture",
        "centered",
    ]
    unique = {tag for tag in combined}
    return [tag for tag in preferred if tag in unique][:3]


def _gap_threshold(source: str) -> float:
    if source == "mix":
        return 2.0
    if source == "vocals":
        return 1.0
    return 0.75


def _max_level(left: str, right: str) -> str:
    order = {"low": 0, "medium": 1, "high": 2}
    return left if order.get(left, 0) >= order.get(right, 0) else right


def _merged_focus(left: str, right: str, tags: list[str]) -> str:
    if any(tag.startswith("low_end") for tag in tags):
        return "low"
    if any(tag.startswith("percussion") or tag.startswith("attack") for tag in tags):
        return "high"
    return left if left == right else "broad"