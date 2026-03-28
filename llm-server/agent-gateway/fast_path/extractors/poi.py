import re
from typing import Any, Dict, List, Optional


def _resolve_poi_id(prompt: str, result: Dict[str, Any]) -> Optional[str]:
    if not isinstance(result, dict) or not result.get("ok"):
        return None
    lowered = str(prompt or "").lower()
    best_match: tuple[int, str] | None = None
    for poi in (result.get("data") or {}).get("pois") or []:
        poi_id = str(poi.get("id") or "").strip()
        poi_name = str(poi.get("name") or "").strip()
        for candidate in [poi_name.lower(), poi_id.lower()]:
            if candidate and re.search(rf"\b{re.escape(candidate)}\b", lowered):
                score = len(candidate)
                if best_match is None or score > best_match[0]:
                    best_match = (score, poi_id)
    return best_match[1] if best_match is not None else None


def _extract_ordered_poi_ids(prompt: str, result: Dict[str, Any]) -> List[str]:
    if not isinstance(result, dict) or not result.get("ok"):
        return []
    lowered = str(prompt or "").lower()
    mentions: List[tuple[int, int, str]] = []
    for poi in (result.get("data") or {}).get("pois") or []:
        poi_id = str(poi.get("id") or "").strip()
        poi_name = str(poi.get("name") or "").strip()
        if not poi_id:
            continue
        for candidate in [poi_name.lower(), poi_id.lower()]:
            if not candidate:
                continue
            for match in re.finditer(rf"\b{re.escape(candidate)}\b", lowered):
                mentions.append((match.start(), -len(candidate), poi_id))
    ordered_ids: List[str] = []
    for _, _, poi_id in sorted(mentions):
        if poi_id not in ordered_ids:
            ordered_ids.append(poi_id)
    return ordered_ids


def _extract_poi_transition(prompt: str, result: Dict[str, Any]) -> Optional[tuple[str, str, Optional[str]]]:
    poi_ids = _extract_ordered_poi_ids(prompt, result)
    if len(poi_ids) < 2:
        return None
    return poi_ids[0], poi_ids[1], poi_ids[2] if len(poi_ids) > 2 else None