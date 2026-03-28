from typing import Any, Dict, List, Optional

from messages import _latest_user_prompt
from fast_path.handlers.chaser import try_chaser_fast_path
from fast_path.handlers.cue_proposals import try_cue_proposals_fast_path
from fast_path.handlers.informational import try_informational_fast_path
from fast_path.handlers.movement import try_movement_fast_path


async def _run_stream_fast_path(messages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    prompt = _latest_user_prompt(messages)
    lowered = prompt.lower()
    for handler in [
        lambda: try_informational_fast_path(messages, prompt, lowered),
        lambda: try_cue_proposals_fast_path(prompt, lowered),
        lambda: try_movement_fast_path(prompt, lowered),
        lambda: try_chaser_fast_path(prompt, lowered),
    ]:
        result = await handler()
        if result is not None:
            return result
    return None