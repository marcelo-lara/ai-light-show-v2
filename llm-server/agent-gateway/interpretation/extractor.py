import json
from typing import Any, Awaitable, Callable, Dict, List, Optional

from interpretation.prompts import _build_section_timing_extraction_messages
from interpretation.schemas import SectionTimingExtraction


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    stripped = str(text or "").strip()
    if not stripped:
        return None
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        return json.loads(stripped[start : end + 1])
    except json.JSONDecodeError:
        return None


async def extract_section_timing_slots(
    messages: List[Dict[str, Any]],
    client: Any,
    model: str,
    llm_complete: Callable[[Any, Dict[str, Any]], Awaitable[Dict[str, Any]]],
) -> Optional[SectionTimingExtraction]:
    response = await llm_complete(
        client,
        {
            "model": model,
            "messages": _build_section_timing_extraction_messages(messages),
            "temperature": 0.0,
            "max_tokens": 64,
            "tools": [],
            "tool_choice": "none",
        },
    )
    content = str(((response.get("choices") or [{}])[0].get("message") or {}).get("content") or "")
    payload = _extract_json_object(content)
    if payload is None:
        return None
    try:
        return SectionTimingExtraction.model_validate(payload)
    except Exception:
        return None
