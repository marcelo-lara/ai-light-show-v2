import re
from typing import Dict, Optional


def _extract_effect_name(prompt: str) -> Optional[str]:
    lowered = str(prompt or "").lower()
    for effect_name in ["flash", "strobe", "full", "fade_in"]:
        if effect_name.replace("_", " ") in lowered or effect_name in lowered:
            return effect_name
    return None


def _extract_color_name(prompt: str) -> Optional[str]:
    lowered = str(prompt or "").lower()
    for color_name in ["blue", "red", "green", "white", "yellow", "cyan", "magenta", "purple", "orange", "pink"]:
        if re.search(rf"\b{re.escape(color_name)}\b", lowered):
            return color_name
    return None


def _color_name_to_rgb(color_name: str) -> Optional[Dict[str, int]]:
    return {
        "blue": {"red": 0, "green": 0, "blue": 255},
        "red": {"red": 255, "green": 0, "blue": 0},
        "green": {"red": 0, "green": 255, "blue": 0},
        "white": {"red": 255, "green": 255, "blue": 255},
        "yellow": {"red": 255, "green": 255, "blue": 0},
        "cyan": {"red": 0, "green": 255, "blue": 255},
        "magenta": {"red": 255, "green": 0, "blue": 255},
        "purple": {"red": 128, "green": 0, "blue": 255},
        "orange": {"red": 255, "green": 128, "blue": 0},
        "pink": {"red": 255, "green": 105, "blue": 180},
    }.get(color_name.lower())