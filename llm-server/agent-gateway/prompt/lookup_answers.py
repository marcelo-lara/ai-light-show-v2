from typing import Any, Dict, List

from messages import _latest_user_prompt
from prompt.instructions import _bar_beat_time_instruction, _song_name_mention_instruction


def _build_section_answer_messages(messages: List[Dict[str, Any]], result: Dict[str, Any]) -> List[Dict[str, str]]:
    original_question = _latest_user_prompt(messages)
    if isinstance(result, dict) and result.get("ok"):
        section = ((result.get("data") or {}).get("section") or {})
        section_block = "section_found=true\n" f"section_name={section.get('name', 'Unnamed')}\nsection_start_seconds={float(section.get('start_s', 0.0)):.3f}\nsection_end_seconds={float(section.get('end_s', 0.0)):.3f}"
    else:
        error = (result.get("error") or {}) if isinstance(result, dict) else {}
        section_block = "section_found=false\n" f"error_code={error.get('code', 'unknown')}\nerror_message={error.get('message', 'unknown')}"
    return [
        {
            "role": "system",
            "content": "Answer only from the resolved section facts provided by the user. " + _song_name_mention_instruction() + _bar_beat_time_instruction() + "If section_found=true, never say the data is missing. Answer the original question directly with the exact numeric time. Use seconds only if bar and beat are unavailable in the resolved facts. Keep the answer to one sentence.",
        },
        {"role": "user", "content": f"Original question: {original_question}\nResolved section facts:\n{section_block}\nAnswer the original question directly."},
    ]


def _build_chord_answer_messages(messages: List[Dict[str, Any]], result: Dict[str, Any]) -> List[Dict[str, str]]:
    original_question = _latest_user_prompt(messages)
    payload = (result.get("data") or {}) if isinstance(result, dict) and result.get("ok") else {}
    chord = payload.get("chord") or {}
    facts = f"occurrence={int(payload.get('occurrence', 1))}\ntime_seconds={float(chord.get('time_s', 0.0)):.3f}\nbar={int(chord.get('bar', 0))}\nbeat={int(chord.get('beat', 0))}\nchord={chord.get('label', 'unknown')}"
    return [
        {"role": "system", "content": "Answer only from the resolved chord facts provided by the user. " + _song_name_mention_instruction() + _bar_beat_time_instruction() + "Report the exact bar.beat first and the exact seconds in parentheses in one sentence."},
        {"role": "user", "content": f"Original question: {original_question}\nResolved chord facts:\n{facts}\nAnswer the original question directly."},
    ]


def _build_cursor_answer_messages(messages: List[Dict[str, Any]], result: Dict[str, Any]) -> List[Dict[str, str]]:
    original_question = _latest_user_prompt(messages)
    payload = (result.get("data") or {}) if isinstance(result, dict) and result.get("ok") else {}
    facts = f"time_seconds={float(payload.get('time_s', 0.0)):.3f}\nbar={payload.get('bar')}\nbeat={payload.get('beat')}\nsection={payload.get('section_name')}"
    return [
        {"role": "system", "content": "Answer only from the resolved cursor facts provided by the user. " + _song_name_mention_instruction() + _bar_beat_time_instruction() + "You must report the exact bar.beat first and the exact seconds in parentheses in one sentence, with no reinterpretation."},
        {"role": "user", "content": f"Original question: {original_question}\nResolved cursor facts:\n{facts}\nAnswer the original question directly."},
    ]


def _is_section_timing_question(messages: List[Dict[str, Any]]) -> bool:
    prompt = _latest_user_prompt(messages).lower()
    if not prompt:
        return False
    if any(token in prompt for token in ["start", "starts", "end", "ends", "begin", "begins"]):
        return True
    return any(token in prompt for token in ["where", "when"]) and any(token in prompt for token in ["intro", "verse", "chorus", "instrumental", "outro", "section"])