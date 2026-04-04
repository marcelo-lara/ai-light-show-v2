from __future__ import annotations

ALLOWED_STEREO_TAGS = {
    "attack_left",
    "attack_right",
    "echo_left",
    "echo_right",
    "low_end_left",
    "low_end_right",
    "percussion_left",
    "percussion_right",
    "ambience_left",
    "ambience_right",
    "split_texture",
    "centered",
}

TAG_ORDER = [
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


def normalize_tags(tags: list[str]) -> list[str]:
    unique = {tag for tag in tags if tag in ALLOWED_STEREO_TAGS}
    return [tag for tag in TAG_ORDER if tag in unique][:3]