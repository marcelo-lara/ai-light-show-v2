from __future__ import annotations

from typing import Any, Dict

from api.intents.llm.prompt_profiles import build_messages, load_prompt_profile


def build_chat_request(prompt: str, model: str, temperature: float) -> Dict[str, Any]:
    profile = load_prompt_profile()
    return {
        "model": model,
        "temperature": temperature,
        "stream": True,
        "messages": build_messages(profile, prompt),
    }