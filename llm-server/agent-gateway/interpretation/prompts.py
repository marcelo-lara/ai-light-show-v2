from typing import Any, Dict, List

from messages import _latest_user_prompt

SECTION_TIMING_EXTRACTION_PROMPT = (
    "You extract structured slots for section timing questions. "
    "Return exactly one compact JSON object on a single line with keys intent, section_name, section_occurrence, boundary. "
    "Do not return markdown. Do not explain. Do not add any text before or after the JSON. "
    "Use intent='section_timing' only when the user is asking when or where a named song section starts or ends. "
    "Use boundary='start' or boundary='end'. "
    "Use section_occurrence=1 when the user does not specify an ordinal. "
    "Use intent='none' when the prompt is not a section timing question."
)


def _should_extract_section_timing(messages: List[Dict[str, Any]]) -> bool:
    prompt = _latest_user_prompt(messages).lower()
    if not prompt:
        return False
    has_timing = any(token in prompt for token in ["when", "where", "start", "starts", "end", "ends", "begin", "begins"])
    has_section = any(token in prompt for token in ["intro", "verse", "chorus", "instrumental", "outro", "section"])
    return has_timing and has_section


def _build_section_timing_extraction_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    return [
        {"role": "system", "content": SECTION_TIMING_EXTRACTION_PROMPT},
        {"role": "user", "content": _latest_user_prompt(messages)},
    ]
