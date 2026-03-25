from __future__ import annotations

from .responses import fail, ok
from .song_data import build_song_details


def register_songs_tools(mcp, runtime) -> None:
    @mcp.tool()
    def songs_list():
        song_service = runtime.require_song_service()
        songs = song_service.list_songs()
        return ok({"songs": songs, "count": len(songs)})

    @mcp.tool()
    def songs_get_details(song: str | None = None):
        ws_manager = runtime.require_ws_manager()
        song_service = runtime.require_song_service()
        current_song = ws_manager.state_manager.current_song
        if song:
            current_song = song_service.load_metadata(song)
        if current_song is None:
            return fail("song_not_loaded", "No song is currently loaded")
        return ok(build_song_details(current_song, ws_manager.state_manager.meta_path))

    @mcp.tool()
    async def songs_load(song: str):
        ws_manager = runtime.require_ws_manager()
        song_service = runtime.require_song_service()
        songs = song_service.list_songs()
        if song not in songs:
            return fail("song_not_found", f"Song '{song}' not found", {"songs": songs})
        try:
            await ws_manager.state_manager.load_song(song)
            await ws_manager.stop_playback_ticker()
            await ws_manager.artnet_service.set_continuous_send(False)
            universe = await ws_manager.state_manager.get_output_universe()
            await ws_manager.artnet_service.update_universe(universe)
            await ws_manager._schedule_broadcast()
        except Exception as exc:
            return fail("song_load_failed", f"Could not load '{song}'", {"error": str(exc)})
        return ok(build_song_details(ws_manager.state_manager.current_song, ws_manager.state_manager.meta_path))