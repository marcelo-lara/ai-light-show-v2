import difflib
import re
from typing import Any, Dict, Optional

ORDINAL_WORD_TO_INDEX = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5}


def _extract_section_name(prompt: str) -> Optional[str]:
    lowered = str(prompt or "").lower()
    section_names = ["intro", "verse", "chorus", "instrumental", "outro"]
    for section_name in section_names:
        if section_name in lowered:
            return section_name.title()
    for word in re.findall(r"[a-z]+", lowered):
        close_match = difflib.get_close_matches(word, section_names, n=1, cutoff=0.7)
        if close_match:
            return close_match[0].title()
    return None


def _extract_section_reference(prompt: str) -> tuple[Optional[str], int]:
    lowered = str(prompt or "").lower()
    match = re.search(r"\b(first|second|third|fourth|fifth|\d+(?:st|nd|rd|th)?)\s+(intro|verse|chorus|instrumental|outro)\b", lowered)
    if match:
        raw_ordinal = match.group(1)
        occurrence = ORDINAL_WORD_TO_INDEX.get(raw_ordinal)
        if occurrence is None:
            occurrence = int(re.sub(r"(?:st|nd|rd|th)$", "", raw_ordinal))
        return match.group(2).title(), max(1, occurrence)
    return _extract_section_name(prompt), 1


def _find_section_occurrence(result: Dict[str, Any], section_name: str, occurrence: int) -> Optional[Dict[str, Any]]:
    if not isinstance(result, dict) or not result.get("ok"):
        return None
    normalized_target = str(section_name or "").strip().lower()
    sections = (result.get("data") or {}).get("sections") or []
    matches = [section for section in sections if str(section.get("name") or section.get("label") or "").strip().lower() == normalized_target]
    if occurrence <= 0 or occurrence > len(matches):
        return None
    return matches[occurrence - 1]


def _section_start_times(result: Dict[str, Any]) -> list[float]:
    if not isinstance(result, dict) or not result.get("ok"):
        return []
    return [float(section.get("start_s", 0.0) or 0.0) for section in ((result.get("data") or {}).get("sections") or [])]