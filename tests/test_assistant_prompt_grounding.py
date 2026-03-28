from pathlib import Path

from backend.services.assistant.prompts import load_prompt


def test_generic_prompt_frames_effects_as_stage_lighting() -> None:
    assistant_root = Path(__file__).resolve().parents[1] / "backend" / "services" / "assistant"

    prompt = load_prompt(assistant_root, "generic").lower()

    assert "physical lighting in a stage or venue space" in prompt
    assert "never as screen, ui, animation, or graphics effects" in prompt
    assert "beams, washes, focus, motion, intensity, and stage transitions" in prompt