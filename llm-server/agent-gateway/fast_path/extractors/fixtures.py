import re
from typing import Any, Dict, List


_FIXTURE_QUALIFIER_STOP_WORDS = {
    "a",
    "an",
    "and",
    "at",
    "make",
    "move",
    "my",
    "of",
    "on",
    "our",
    "point",
    "set",
    "the",
    "this",
    "to",
    "turn",
}


def _fixture_rows(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(result, dict) or not result.get("ok"):
        return []
    fixtures = ((result.get("data") or {}).get("fixtures") or [])
    return [fixture for fixture in fixtures if isinstance(fixture, dict)]


def _normalize_fixture_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _extract_type_qualifier(prompt: str, labels: list[str]) -> str | None:
    lowered = str(prompt or "").lower()
    for label in sorted(labels, key=len, reverse=True):
        index = lowered.find(label)
        if index < 0:
            continue
        tokens = re.findall(r"[a-z0-9-]+", lowered[:index])
        qualifier_tokens: list[str] = []
        for token in reversed(tokens):
            if token in _FIXTURE_QUALIFIER_STOP_WORDS:
                break
            qualifier_tokens.append(token)
            if len(qualifier_tokens) >= 2:
                break
        if qualifier_tokens:
            return " ".join(reversed(qualifier_tokens)).strip()
    return None


def _matches_fixture_alias(lowered: str, normalized_prompt: str, fixture: Dict[str, Any]) -> bool:
    fixture_id = str(fixture.get("id") or "")
    fixture_name = str(fixture.get("name") or "")
    normalized_id = _normalize_fixture_text(fixture_id)
    normalized_name = _normalize_fixture_text(fixture_name)
    return bool(
        fixture_id and re.search(rf"\b{re.escape(fixture_id.lower())}\b", lowered)
        or normalized_id and normalized_id in normalized_prompt
        or normalized_name and normalized_name in normalized_prompt
    )


def _fixture_type_matches(fixture: Dict[str, Any], fixture_type: str) -> bool:
    return str(fixture.get("type") or "").strip().lower() == fixture_type


def _filter_fixture_ids_by_qualifier(result: Dict[str, Any], fixture_ids: List[str], qualifier: str) -> List[str]:
    normalized_qualifier = _normalize_fixture_text(qualifier)
    if not normalized_qualifier:
        return list(fixture_ids)
    fixtures = {str(fixture.get("id") or "").strip(): fixture for fixture in _fixture_rows(result)}
    matches: List[str] = []
    for fixture_id in fixture_ids:
        fixture = fixtures.get(fixture_id)
        if fixture is None:
            continue
        normalized_id = _normalize_fixture_text(fixture_id)
        normalized_name = _normalize_fixture_text(str(fixture.get("name") or ""))
        if normalized_qualifier in normalized_id or normalized_qualifier in normalized_name:
            matches.append(fixture_id)
    return matches


def _resolve_fixture_ids_by_type(result: Dict[str, Any], fixture_type: str) -> List[str]:
    ids = [str(fixture.get("id") or "") for fixture in _fixture_rows(result) if _fixture_type_matches(fixture, fixture_type)]
    return [fixture_id for fixture_id in ids if fixture_id]


def _resolve_moving_head_fixture_ids(result: Dict[str, Any]) -> List[str]:
    return _resolve_fixture_ids_by_type(result, "moving_head")


def _extract_moving_head_qualifier(prompt: str) -> str | None:
    return _extract_type_qualifier(prompt, ["moving head", "moving heads"])


def _resolve_prism_fixture_ids(result: Dict[str, Any]) -> List[str]:
    ids = [str(fixture.get("id") or "") for fixture in _fixture_rows(result) if "prism" in str(fixture.get("id") or "").lower()]
    return [fixture_id for fixture_id in ids if fixture_id]


def _resolve_left_prism_fixture_ids(result: Dict[str, Any]) -> List[str]:
    return [fixture_id for fixture_id in _resolve_prism_fixture_ids(result) if fixture_id.endswith("_l")]


def _resolve_right_prism_fixture_ids(result: Dict[str, Any]) -> List[str]:
    return [fixture_id for fixture_id in _resolve_prism_fixture_ids(result) if fixture_id.endswith("_r")]


def _resolve_target_prism_fixture_ids(prompt: str, result: Dict[str, Any]) -> List[str]:
    lowered = str(prompt or "").lower()
    if "right" in lowered:
        return _resolve_right_prism_fixture_ids(result)
    if "left" in lowered:
        return _resolve_left_prism_fixture_ids(result)
    return _resolve_prism_fixture_ids(result)


def _resolve_parcan_fixture_ids(result: Dict[str, Any]) -> List[str]:
    ids = [str(fixture.get("id") or "") for fixture in _fixture_rows(result) if str(fixture.get("id") or "").lower().startswith("parcan")]
    return [fixture_id for fixture_id in ids if fixture_id]


def _resolve_proton_fixture_ids(result: Dict[str, Any]) -> List[str]:
    return [fixture_id for fixture_id in _resolve_parcan_fixture_ids(result) if fixture_id.endswith(("_pl", "_pr"))]


def _resolve_non_parcan_fixture_ids(result: Dict[str, Any]) -> List[str]:
    ids = [str(fixture.get("id") or "") for fixture in _fixture_rows(result) if not str(fixture.get("id") or "").lower().startswith("parcan")]
    return [fixture_id for fixture_id in ids if fixture_id]


def _resolve_fixture_ids_from_prompt(prompt: str, result: Dict[str, Any]) -> List[str]:
    lowered = str(prompt or "").lower()
    normalized_prompt = _normalize_fixture_text(prompt)
    fixtures = _fixture_rows(result)
    explicit_ids = [str(fixture.get("id") or "") for fixture in fixtures if _matches_fixture_alias(lowered, normalized_prompt, fixture)]
    if explicit_ids:
        return explicit_ids
    if "moving head" in lowered or "moving heads" in lowered:
        moving_head_ids = _resolve_moving_head_fixture_ids(result)
        qualifier = _extract_moving_head_qualifier(prompt)
        if qualifier is not None:
            return _filter_fixture_ids_by_qualifier(result, moving_head_ids, qualifier)
        return moving_head_ids
    if "prism" in lowered:
        return _resolve_target_prism_fixture_ids(prompt, result)
    if "parcan" in lowered:
        return _resolve_parcan_fixture_ids(result)
    return []