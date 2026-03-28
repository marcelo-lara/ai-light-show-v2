import re
from typing import Any, Dict, List


def _resolve_prism_fixture_ids(result: Dict[str, Any]) -> List[str]:
    if not isinstance(result, dict) or not result.get("ok"):
        return []
    ids = [str(fixture.get("id") or "") for fixture in ((result.get("data") or {}).get("fixtures") or []) if "prism" in str(fixture.get("id") or "").lower()]
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
    if not isinstance(result, dict) or not result.get("ok"):
        return []
    ids = [str(fixture.get("id") or "") for fixture in ((result.get("data") or {}).get("fixtures") or []) if str(fixture.get("id") or "").lower().startswith("parcan")]
    return [fixture_id for fixture_id in ids if fixture_id]


def _resolve_proton_fixture_ids(result: Dict[str, Any]) -> List[str]:
    return [fixture_id for fixture_id in _resolve_parcan_fixture_ids(result) if fixture_id.endswith(("_pl", "_pr"))]


def _resolve_non_parcan_fixture_ids(result: Dict[str, Any]) -> List[str]:
    if not isinstance(result, dict) or not result.get("ok"):
        return []
    ids = [str(fixture.get("id") or "") for fixture in ((result.get("data") or {}).get("fixtures") or []) if not str(fixture.get("id") or "").lower().startswith("parcan")]
    return [fixture_id for fixture_id in ids if fixture_id]


def _resolve_fixture_ids_from_prompt(prompt: str, result: Dict[str, Any]) -> List[str]:
    if not isinstance(result, dict) or not result.get("ok"):
        return []
    lowered = str(prompt or "").lower()
    fixtures = (result.get("data") or {}).get("fixtures") or []
    explicit_ids = [str(fixture.get("id") or "") for fixture in fixtures if str(fixture.get("id") or "") and re.search(rf"\b{re.escape(str(fixture.get('id') or '').lower())}\b", lowered)]
    if explicit_ids:
        return explicit_ids
    if "prism" in lowered:
        return _resolve_target_prism_fixture_ids(prompt, result)
    if "parcan" in lowered:
        return _resolve_parcan_fixture_ids(result)
    return []