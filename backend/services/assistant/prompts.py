from __future__ import annotations

from pathlib import Path


PROMPT_FILES = {
    "generic": "generic.txt",
}


def load_prompt(assistant_root: Path, assistant_id: str) -> str:
    prompt_file = PROMPT_FILES.get(assistant_id, PROMPT_FILES["generic"])
    prompt_path = assistant_root / "prompts" / prompt_file
    return prompt_path.read_text(encoding="utf-8").strip()