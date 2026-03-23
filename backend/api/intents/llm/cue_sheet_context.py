from __future__ import annotations

from typing import Any, Dict, List


def build_cue_sheet_payload(manager) -> Dict[str, Any]:
    entries = list(getattr(manager.state_manager, "get_cue_entries", lambda: [])() or [])
    indexed_entries: List[Dict[str, Any]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        indexed_entries.append({"index": index, **entry})

    return {
        "song_id": str(getattr(getattr(manager.state_manager, "current_song", None), "song_id", "") or ""),
        "entry_count": len(indexed_entries),
        "entries": indexed_entries,
    }


def build_cue_sheet_context(manager) -> str:
    payload = build_cue_sheet_payload(manager)
    lines = [
        "Current cue sheet summary:",
        f"- Song id: {payload['song_id'] or 'unavailable'}",
        f"- Cue entries: {payload['entry_count']}",
        "- Use the cue-sheet retrieval tool for exact cue rows before suggesting edits.",
    ]
    return "\n".join(lines)