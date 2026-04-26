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

    @mcp.tool()
    async def chasers_list():
        ws_manager = runtime.require_ws_manager()
        return ok({"chasers": ws_manager.state_manager.get_chasers(), "count": len(ws_manager.state_manager.get_chasers())})

    @mcp.tool()
    async def chasers_upsert_definition(
        id: str,
        name: str,
        description: str,
        effects: list[dict],
        is_global: bool = False
    ):
        """
        Creates or updates a chaser definition.
        By default, chasers are saved as 'local' to the currently loaded song.
        If is_global is True, it is saved to the shared library (requires caution).
        """
        ws_manager = runtime.require_ws_manager()
        res = await ws_manager.state_manager.upsert_chaser_definition(
            chaser_id=id,
            name=name,
            description=description,
            effects=effects,
            is_global=is_global
        )
        if not res.get("ok"):
            return fail("chaser_upsert_failed", res.get("reason", "Unknown error"))
        
        return ok(res)