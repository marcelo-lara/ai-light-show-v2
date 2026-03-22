from __future__ import annotations

from typing import Any, Dict

from api.intents.llm.prompt_profiles import build_messages, load_prompt_profile
from api.intents.llm.song_context import build_fixture_context, build_song_context


def build_chat_request(manager, prompt: str, model: str, temperature: float) -> Dict[str, Any]:
    profile = load_prompt_profile()
    context = "\n\n".join([build_song_context(manager), build_fixture_context(manager)])
    return {
        "model": model,
        "temperature": temperature,
        "stream": True,
        "messages": build_messages(profile, prompt, context),
    }