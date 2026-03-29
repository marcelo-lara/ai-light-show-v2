from __future__ import annotations
from .responses import fail, ok

def register_pois_tools(mcp, runtime) -> None:
    @mcp.tool()
    async def pois_list():
        """
        List all Points of Interest (POIs).
        POIs are named locations (e.g., 'piano', 'table', 'center') that fixtures can move to or sweep towards.
        By providing the POI ID, you can use 'move_to_poi' or similar effects in your cues.
        """
        ws_manager = runtime.require_ws_manager()
        pois = await ws_manager.state_manager.poi_db.get_all()
        return ok({"pois": pois, "count": len(pois)})
    
    @mcp.tool()
    async def pois_get(poi_id: str):
        """
        Get a specific Point of Interest (POI) by its ID.
        """
        ws_manager = runtime.require_ws_manager()
        poi = await ws_manager.state_manager.poi_db.get(poi_id)
        if poi is None:
            return fail("poi_not_found", f"POI '{poi_id}' not found")
        return ok(poi)
