from typing import Any, Dict, List

from messages import _latest_user_prompt
from prompt.instructions import _bar_beat_time_instruction, _song_name_mention_instruction


def _build_first_effect_answer_messages(messages: List[Dict[str, Any]], section_result: Dict[str, Any], cue_result: Dict[str, Any]) -> List[Dict[str, str]]:
    original_question = _latest_user_prompt(messages)
    section = ((section_result.get("data") or {}).get("section") or {}) if section_result.get("ok") else {}
    entries = ((cue_result.get("data") or {}).get("entries") or []) if cue_result.get("ok") else []
    effect_entries = [entry for entry in entries if entry.get("fixture_id") and entry.get("effect")]
    earliest_time = min(float(entry.get("time", 0.0)) for entry in effect_entries)
    earliest_entries = [entry for entry in effect_entries if float(entry.get("time", 0.0)) == earliest_time]
    facts = f"section_name={section.get('name', 'unknown')}\nsection_start_seconds={float(section.get('start_s', 0.0)):.3f}\nfirst_effect_time_seconds={earliest_time:.3f}\nfixtures={', '.join(str(entry.get('fixture_id')) for entry in earliest_entries)}\neffect={str(earliest_entries[0].get('effect') or '')}\nduration_seconds={float(earliest_entries[0].get('duration', 0.0)):.3f}"
    return [
        {"role": "system", "content": "Answer only from the resolved section and cue facts provided by the user. " + _song_name_mention_instruction() + _bar_beat_time_instruction() + "If bar and beat for the first effect are unavailable in the resolved facts, use seconds. Use exactly one sentence in this structure: At <bar>.<beat> (<first_effect_time_seconds>s), <fixtures> <effect> for <duration_seconds>s. If bar and beat are unavailable, use: At <first_effect_time_seconds>s, <fixtures> <effect> for <duration_seconds>s."},
        {"role": "user", "content": f"Original question: {original_question}\nResolved facts:\n{facts}\nAnswer the original question directly."},
    ]


def _build_loudness_answer_messages(messages: List[Dict[str, Any]], loudness_result: Dict[str, Any]) -> List[Dict[str, str]]:
    original_question = _latest_user_prompt(messages)
    payload = (loudness_result.get("data") or {}) if loudness_result.get("ok") else {}
    facts = f"start_time={float(payload.get('start_time', 0.0)):.3f}\nend_time={float(payload.get('end_time', 0.0)):.3f}\naverage={float(payload.get('average', 0.0)):.6f}\nminimum={float(payload.get('minimum', 0.0)):.6f}\nmaximum={float(payload.get('maximum', 0.0)):.6f}"
    return [
        {"role": "system", "content": "Answer only from the resolved loudness facts provided by the user. " + _song_name_mention_instruction() + _bar_beat_time_instruction() + "If bar and beat facts are unavailable for the time range, use seconds. Use exactly one sentence in this structure: The first verse spans <start_bar>.<start_beat> (<start_time>s) to <end_bar>.<end_beat> (<end_time>s) and has average loudness <average>. If bar and beat are unavailable, use seconds only."},
        {"role": "user", "content": f"Original question: {original_question}\nResolved loudness facts:\n{facts}\nAnswer the original question directly."},
    ]


def _build_fixtures_at_bar_answer_messages(messages: List[Dict[str, Any]], position_result: Dict[str, Any], cue_result: Dict[str, Any]) -> List[Dict[str, str]]:
    original_question = _latest_user_prompt(messages)
    position = ((position_result.get("data") or {}).get("position") or {}) if position_result.get("ok") else {}
    entries = ((cue_result.get("data") or {}).get("entries") or []) if cue_result.get("ok") else []
    effect_entries = [entry for entry in entries if entry.get("fixture_id") and entry.get("effect")]
    facts = f"time_seconds={float(position.get('time', 0.0)):.3f}\nbar={int(position.get('bar', 0))}\nbeat={int(position.get('beat', 0))}\nfixtures={', '.join(str(entry.get('fixture_id')) for entry in effect_entries)}\neffect={str(effect_entries[0].get('effect') or '')}\nduration_seconds={float(effect_entries[0].get('duration', 0.0)) if effect_entries else 0.0:.3f}"
    return [
        {"role": "system", "content": "Answer only from the resolved musical position and cue facts provided by the user. " + _song_name_mention_instruction() + _bar_beat_time_instruction() + "Use exactly one sentence in this structure: At <bar>.<beat> (<time_seconds>s), <fixtures> <effect> for <duration_seconds>s."},
        {"role": "user", "content": f"Original question: {original_question}\nResolved facts:\n{facts}\nAnswer the original question directly."},
    ]


def _build_left_fixtures_answer_messages(messages: List[Dict[str, Any]], fixtures_result: Dict[str, Any]) -> List[Dict[str, str]]:
    original_question = _latest_user_prompt(messages)
    fixtures = ((fixtures_result.get("data") or {}).get("fixtures") or []) if fixtures_result.get("ok") else []
    left_ids = [str(fixture.get("id")) for fixture in fixtures if str(fixture.get("id") or "").endswith(("_l", "_pl"))]
    return [
        {"role": "system", "content": "Answer only from the resolved fixture facts provided by the user. " + _song_name_mention_instruction() + "Repeat every id from left_fixture_ids exactly once, comma-separated, with no omissions."},
        {"role": "user", "content": f"Original question: {original_question}\nResolved fixture facts:\nleft_fixture_ids={', '.join(left_ids)}\nAnswer the original question directly."},
    ]