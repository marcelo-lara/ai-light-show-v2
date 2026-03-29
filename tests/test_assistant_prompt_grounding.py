from pathlib import Path

from backend.services.assistant.prompts import load_prompt


def test_generic_prompt_frames_effects_as_stage_lighting() -> None:
    assistant_root = Path(__file__).resolve().parents[1] / "backend" / "services" / "assistant"

    prompt = load_prompt(assistant_root, "generic").lower()

    assert "physical lighting in a stage space" in prompt
    assert "never as screen, ui, animation, or graphics effects" in prompt
    assert "beams, washes, focus, motion, intensity, and stage transitions" in prompt
    assert "resolve the target fixture ids with the fixture tool and the destination with the poi tool" in prompt
    assert "if the request changes cues and does not include an explicit time or section, resolve the current cursor time" in prompt
    assert "prefer a move_to_poi cue proposal" in prompt