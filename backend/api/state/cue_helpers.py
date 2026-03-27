from __future__ import annotations

from typing import Any, Dict, List

from services.cue_helpers import build_cue_helper_definitions


def build_cue_helpers_payload() -> List[Dict[str, Any]]:
    """Build the cue helpers payload for frontend state.

    Returns a list of available cue helper definitions.
    """
    return build_cue_helper_definitions()