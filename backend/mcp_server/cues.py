from __future__ import annotations

from .responses import fail, ok


def register_cue_tools(mcp, runtime) -> None:
    @mcp.tool()
    def cues_get_sheet():
        ws_manager = runtime.require_ws_manager()
        entries = ws_manager.state_manager.get_cue_entries()
        song = getattr(getattr(ws_manager.state_manager, "current_song", None), "song_id", None)
        return ok({"song": song, "entries": entries, "count": len(entries)})

    @mcp.tool()
    def cues_get_window(start_time: float, end_time: float):
        ws_manager = runtime.require_ws_manager()
        try:
            entries = ws_manager.state_manager.get_cue_entries_window(float(start_time), float(end_time))
        except ValueError as exc:
            return fail("invalid_time_range", str(exc))
        return ok({"start_time": float(start_time), "end_time": float(end_time), "entries": entries, "count": len(entries)})

    @mcp.tool()
    async def cues_add_entry(entry: dict):
        ws_manager = runtime.require_ws_manager()
        if not isinstance(entry, dict):
            return fail("invalid_entry", "Entry must be an object")
        try:
            time_value = float(entry.get("time"))
        except Exception:
            return fail("missing_time", "Cue entry requires a numeric time")
        if entry.get("chaser_id"):
            result = await ws_manager.state_manager.add_chaser_cue_entry(time_value, str(entry.get("chaser_id")), entry.get("data") or {})
        else:
            result = await ws_manager.state_manager.add_effect_cue_entry(time_value, str(entry.get("fixture_id") or ""), str(entry.get("effect") or ""), float(entry.get("duration", 0.0) or 0.0), entry.get("data") or {})
        if not result.get("ok"):
            return fail("cue_add_failed", "Could not add cue entry", result)
        await ws_manager._schedule_broadcast()
        return ok(result)

    @mcp.tool()
    async def cues_update_entry(index: int, patch: dict):
        ws_manager = runtime.require_ws_manager()
        result = await ws_manager.state_manager.update_cue_entry(int(index), patch or {})
        if not result.get("ok"):
            return fail("cue_update_failed", "Could not update cue entry", result)
        await ws_manager._schedule_broadcast()
        return ok(result)

    @mcp.tool()
    async def cues_delete_entry(index: int):
        ws_manager = runtime.require_ws_manager()
        result = await ws_manager.state_manager.delete_cue_entry(int(index))
        if not result.get("ok"):
            return fail("cue_delete_failed", "Could not delete cue entry", result)
        await ws_manager._schedule_broadcast()
        return ok(result)

    @mcp.tool()
    async def cues_replace_sheet(entries: list[dict]):
        ws_manager = runtime.require_ws_manager()
        result = await ws_manager.state_manager.replace_cue_sheet_entries(entries or [])
        if not result.get("ok"):
            return fail("cue_replace_failed", "Could not replace cue sheet", result)
        await ws_manager._schedule_broadcast()
        return ok(result)