from typing import Any, Dict, List, Optional

from fast_path.extractors.sections import _extract_section_reference
from fast_path.proposals import _proposal_for_tool
from gateway_mcp.client import call_mcp


async def try_chaser_fast_path(prompt: str, lowered: str) -> Optional[Dict[str, Any]]:
    section_name, _section_occurrence = _extract_section_reference(prompt)
    if not ("chaser" in lowered and "parcan" in lowered and section_name):
        return None
    used_tools: List[str] = ["mcp_find_section"]
    section_result = await call_mcp("mcp_find_section", {"section_name": section_name})
    section = ((section_result.get("data") or {}).get("section") or {}) if isinstance(section_result, dict) else {}
    if not section:
        return None
    used_tools.append("mcp_read_beats")
    beats_result = await call_mcp("mcp_read_beats", {"start_time": float(section.get("start_s", 0.0)), "end_time": float(section.get("end_s", 0.0))})
    beat_count = int(((beats_result.get("data") or {}).get("count") or 0)) if isinstance(beats_result, dict) else 0
    return {"used_tools": used_tools, "proposal": _proposal_for_tool("propose_chaser_apply", {"chaser_id": "parcan_left_to_right", "start_time": float(section.get("start_s", 0.0)), "repetitions": max(1, beat_count // 4)})}