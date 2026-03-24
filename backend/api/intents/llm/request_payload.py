from __future__ import annotations

from typing import Any, Dict, Iterable, List

from api.intents.llm.cue_sheet_context import build_cue_sheet_context
from api.intents.llm.playback_context import build_playback_position_context
from api.intents.llm.prompt_profiles import build_messages, load_prompt_profile
from api.intents.llm.song_context import build_fixture_context, build_song_context


MAX_HISTORY_MESSAGES = 20


def _normalize_history(history: Iterable[Dict[str, Any]] | None) -> List[Dict[str, str]]:
	if history is None:
		return []

	normalized: List[Dict[str, str]] = []
	for message in history:
		if not isinstance(message, dict):
			continue
		role = str(message.get("role") or "").strip().lower()
		content = str(message.get("content") or "").strip()
		if role not in {"user", "assistant"} or not content:
			continue
		normalized.append({"role": role, "content": content})
	return normalized[-MAX_HISTORY_MESSAGES:]


async def build_chat_request(
	manager,
	prompt: str,
	model: str,
	temperature: float,
	history: Iterable[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
	profile = load_prompt_profile()
	context = "\n\n".join(
		[
			build_song_context(manager),
			await build_playback_position_context(manager),
			build_fixture_context(manager),
			build_cue_sheet_context(manager),
		]
	)
	messages = build_messages(profile, prompt, context)
	messages[2:2] = _normalize_history(history)
	return {
		"model": model,
		"temperature": temperature,
		"stream": True,
		"tool_choice": "required",
		"messages": messages,
	}
