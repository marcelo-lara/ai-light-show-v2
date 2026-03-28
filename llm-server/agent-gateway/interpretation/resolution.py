from typing import Any, Awaitable, Callable, Dict, List, Optional

from fast_path.extractors.sections import _extract_section_reference, _find_section_occurrence
from interpretation.extractor import extract_section_timing_slots
from interpretation.prompts import _should_extract_section_timing
from messages import _latest_user_prompt


ORDINAL_WORDS = {
    1: "first",
    2: "second",
    3: "third",
    4: "fourth",
    5: "fifth",
}


def _describe_section_reference(section_name: str, occurrence: int) -> str:
    if occurrence <= 1:
        return f"the {section_name.lower()}"
    ordinal = ORDINAL_WORDS.get(occurrence, f"{occurrence}th")
    return f"the {ordinal} {section_name.lower()}"


def _build_section_timing_answer_text(slots, section_result: Dict[str, Any]) -> str:
    if not section_result.get("ok"):
        return str((section_result.get("error") or {}).get("message") or "The requested section was not found.")
    section = ((section_result.get("data") or {}).get("section") or {})
    section_name = str(section.get("name") or slots.section_name or "section")
    boundary = "end" if slots.boundary == "end" else "start"
    time_value = float(section.get("end_s" if boundary == "end" else "start_s", 0.0) or 0.0)
    verb = "ends" if boundary == "end" else "starts"
    return f"{_describe_section_reference(section_name, max(1, slots.section_occurrence)).capitalize()} {verb} at {time_value:.3f} seconds."


def _normalize_section_slots(messages: List[Dict[str, Any]], slots):
    raw_section_name = str(slots.section_name or "")
    extracted_name, extracted_occurrence = _extract_section_reference(raw_section_name)
    if extracted_name and raw_section_name.strip().lower() != extracted_name.strip().lower():
        slots.section_name = extracted_name
        slots.section_occurrence = max(1, extracted_occurrence)
        return slots
    prompt_name, prompt_occurrence = _extract_section_reference(_latest_user_prompt(messages))
    if prompt_name and (not slots.section_name or slots.section_occurrence <= 1):
        slots.section_name = prompt_name
        slots.section_occurrence = max(1, prompt_occurrence)
    return slots


async def try_section_timing_interpretation(
    messages: List[Dict[str, Any]],
    client: Any,
    model: str,
    llm_complete: Callable[[Any, Dict[str, Any]], Awaitable[Dict[str, Any]]],
    call_mcp_fn: Callable[[str, Dict[str, Any]], Awaitable[Any]],
) -> Optional[Dict[str, Any]]:
    if not _should_extract_section_timing(messages):
        return None
    slots = await extract_section_timing_slots(messages, client, model, llm_complete)
    if slots is None or slots.intent != "section_timing" or not slots.section_name:
        return None
    slots = _normalize_section_slots(messages, slots)
    sections_result = await call_mcp_fn("mcp_read_sections", {})
    section = _find_section_occurrence(sections_result, slots.section_name, max(1, slots.section_occurrence))
    if section is None:
        return {
            "used_tools": ["mcp_read_sections"],
            "error": {
                "code": "section_not_found",
                "detail": f"Section '{slots.section_name}' occurrence {max(1, slots.section_occurrence)} was not found.",
                "retryable": False,
            },
        }
    section_result = {
        "ok": True,
        "data": {
            "section": {
                "name": section.get("name") or slots.section_name,
                "start_s": float(section.get("start_s", 0.0) or 0.0),
                "end_s": float(section.get("end_s", 0.0) or 0.0),
            }
        },
    }
    return {
        "used_tools": ["mcp_read_sections"],
        "answer_text": _build_section_timing_answer_text(slots, section_result),
    }
