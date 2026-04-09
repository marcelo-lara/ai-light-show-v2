from typing import Any, Dict

from fastmcp import Client

from config import MCP_BASE_URL, MCP_TOOL_MAP


async def _call_mcp_tool(name: str, arguments: Dict[str, Any]) -> Any:
    async with Client(MCP_BASE_URL) as client:
        result = await client.call_tool(name, arguments, raise_on_error=False)
    if result.is_error:
        detail = None
        if result.content:
            text_value = getattr(result.content[0], "text", None)
            if isinstance(text_value, str):
                detail = text_value
        return {"ok": False, "error": {"code": "mcp_call_failed", "message": detail or f"Tool '{name}' failed"}}
    return result.data if result.data is not None else result.structured_content


async def call_mcp(tool_name: str, args: Dict[str, Any]) -> Any:
    if tool_name not in MCP_TOOL_MAP:
        return {
            "error": "MCP_TOOL_NOT_MAPPED",
            "tool_name": tool_name,
            "available_mappings": list(MCP_TOOL_MAP.keys()),
            "hint": "Call /debug/mcp/tools and map MCP_TOOL_MAP to real tool names.",
        }
    if tool_name == "mcp_load_song":
        return await _call_mcp_tool(MCP_TOOL_MAP[tool_name], {"song": str(args.get("song") or args.get("song_id") or "")})
    if tool_name == "mcp_read_sections":
        song = str(args.get("song") or args.get("song_id") or "")
        return await _call_mcp_tool(MCP_TOOL_MAP[tool_name], {"song": song} if song else {})
    if tool_name == "mcp_read_section_analysis":
        song = str(args.get("song") or args.get("song_id") or "")
        payload = {}
        if song:
            payload["song"] = song
        if args.get("section_name"):
            payload["section_name"] = str(args.get("section_name") or "")
        return await _call_mcp_tool(MCP_TOOL_MAP[tool_name], payload)
    if tool_name == "mcp_find_section":
        return await _call_mcp_tool(MCP_TOOL_MAP[tool_name], {"section_name": str(args.get("section_name") or "")})
    if tool_name == "mcp_find_bar_beat":
        song = str(args.get("song") or args.get("song_id") or "")
        payload: Dict[str, Any] = {"bar": int(args.get("bar", 0)), "beat": int(args.get("beat", 0))}
        if song:
            payload["song"] = song
        return await _call_mcp_tool(MCP_TOOL_MAP[tool_name], payload)
    if tool_name == "mcp_find_chord":
        song = str(args.get("song") or args.get("song_id") or "")
        payload = {"chord": str(args.get("chord") or ""), "occurrence": int(args.get("occurrence", 1) or 1)}
        if song:
            payload["song"] = song
        return await _call_mcp_tool(MCP_TOOL_MAP[tool_name], payload)
    if tool_name in {"mcp_read_beats", "mcp_read_chords", "mcp_read_loudness", "mcp_read_bar_beats"}:
        song = str(args.get("song") or args.get("song_id") or "")
        payload = {key: value for key, value in args.items() if key in {"start_time", "end_time", "section", "start_bar", "start_beat", "end_bar", "end_beat"}}
        if song:
            payload["song"] = song
        return await _call_mcp_tool(MCP_TOOL_MAP[tool_name], payload)
    if tool_name == "mcp_read_cue_sheet":
        return await _call_mcp_tool(MCP_TOOL_MAP[tool_name], {})
    if tool_name == "mcp_read_cue_window":
        payload = {"start_time": float(args.get("start_time", 0.0)), "end_time": float(args.get("end_time", 0.0))}
        return await _call_mcp_tool(MCP_TOOL_MAP[tool_name], payload)
    if tool_name == "mcp_replace_cue_window":
        payload = {
            "start_time": float(args.get("start_time", 0.0)),
            "end_time": float(args.get("end_time", 0.0)),
            "entries": list(args.get("entries") or []),
        }
        return await _call_mcp_tool(MCP_TOOL_MAP[tool_name], payload)
    if tool_name == "mcp_read_fixture_output_window":
        payload = {
            "fixture_id": str(args.get("fixture_id") or ""),
            "start_time": float(args.get("start_time", 0.0)),
            "end_time": float(args.get("end_time", 0.0)),
        }
        if args.get("max_samples") is not None:
            payload["max_samples"] = int(args.get("max_samples") or 0)
        return await _call_mcp_tool(MCP_TOOL_MAP[tool_name], payload)
    return await _call_mcp_tool(MCP_TOOL_MAP[tool_name], args)
