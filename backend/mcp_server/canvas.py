from __future__ import annotations

from .responses import fail, ok


def register_canvas_tools(mcp, runtime) -> None:
    @mcp.tool()
    async def render_dmx_canvas():
        ws_manager = runtime.require_ws_manager()
        result = await ws_manager.state_manager.rerender_dmx_canvas()
        if not result.get("ok"):
            return fail("dmx_render_failed", "Could not render DMX canvas", result)
        return ok(result)

    @mcp.tool()
    async def read_fixture_output_window(
        fixture_id: str,
        start_time: float,
        end_time: float,
        max_samples: int = 240,
    ):
        ws_manager = runtime.require_ws_manager()
        result = await ws_manager.state_manager.read_fixture_output_window(
            fixture_id=str(fixture_id or "").strip(),
            start_time=float(start_time),
            end_time=float(end_time),
            max_samples=int(max_samples or 240),
        )
        if not result.get("ok"):
            return fail("fixture_output_read_failed", "Could not read fixture output window", result)
        return ok(result)