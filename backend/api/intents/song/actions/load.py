from __future__ import annotations

from typing import Any, Dict


async def load_song(manager, payload: Dict[str, Any]) -> bool:
    filename = str(payload.get("filename") or "").strip()
    if not filename:
        await manager.broadcast_event("error", "song_load_failed", {"reason": "missing_filename"})
        return False

    available_songs = manager.song_service.list_songs()
    if filename not in available_songs:
        await manager.broadcast_event(
            "error",
            "song_load_failed",
            {"reason": "unknown_song", "filename": filename, "songs": available_songs},
        )
        return False

    try:
        await manager.state_manager.load_song(filename)
        await manager.stop_playback_ticker()
        await manager.artnet_service.set_continuous_send(False)
        universe = await manager.state_manager.get_output_universe()
        await manager.artnet_service.update_universe(universe)
    except Exception as exc:
        await manager.broadcast_event(
            "error",
            "song_load_failed",
            {"reason": "load_failed", "filename": filename, "error": str(exc)},
        )
        return False

    await manager.broadcast_event("info", "song_loaded", {"filename": filename})
    return True