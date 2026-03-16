from __future__ import annotations

from typing import Any, Dict, List


def build_cue_helpers_payload() -> List[Dict[str, Any]]:
    """Build the cue helpers payload for frontend state.

    Returns a list of available cue helper definitions.
    """
    return [
        {
            "id": "downbeats_and_beats",
            "label": "DownBeats and Beats",
            "description": "Flash mini beams on downbeats, then chase blue on parcans through beats",
            "mode": "full_song",
        }
    ]