from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROMPT_ROOT = Path(__file__).with_name("prompt_profiles")
USER_REQUEST_PLACEHOLDER = "{{user_request}}"


@dataclass(frozen=True)
class PromptProfile:
    name: str
    system_text: str
    instructions_text: str
    user_template: str


def load_prompt_profile(name: str = "default_chat") -> PromptProfile:
    profile_dir = PROMPT_ROOT / name
    return PromptProfile(
        name=name,
        system_text=_read_required_text(profile_dir / "system.txt"),
        instructions_text=_read_required_text(profile_dir / "instructions.txt"),
        user_template=_read_required_text(profile_dir / "user.txt"),
    )


def build_messages(profile: PromptProfile, user_request: str) -> list[dict[str, str]]:
    if USER_REQUEST_PLACEHOLDER not in profile.user_template:
        raise ValueError(f"Prompt profile '{profile.name}' is missing {USER_REQUEST_PLACEHOLDER}")
    return [
        {"role": "system", "content": profile.system_text.strip()},
        {"role": "system", "content": profile.instructions_text.strip()},
        {
            "role": "user",
            "content": profile.user_template.replace(USER_REQUEST_PLACEHOLDER, user_request).strip(),
        },
    ]


def _read_required_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Prompt profile file is empty: {path}")
    return text