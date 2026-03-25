from __future__ import annotations

from api.state.fixtures import build_fixtures_payload

from .responses import fail, ok


def register_fixtures_tools(mcp, runtime) -> None:
    @mcp.tool()
    async def fixtures_list():
        ws_manager = runtime.require_ws_manager()
        universe = await ws_manager.state_manager.get_output_universe()
        fixtures = build_fixtures_payload(ws_manager, universe)
        return ok({"fixtures": list(fixtures.values()), "count": len(fixtures)})

    @mcp.tool()
    async def fixtures_get(fixture_id: str):
        ws_manager = runtime.require_ws_manager()
        universe = await ws_manager.state_manager.get_output_universe()
        fixtures = build_fixtures_payload(ws_manager, universe)
        fixture = fixtures.get(fixture_id)
        if fixture is None:
            return fail("fixture_not_found", f"Fixture '{fixture_id}' not found")
        return ok(fixture)