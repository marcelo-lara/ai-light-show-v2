from typing import Any, Dict

async def update_fixture_target(manager, payload: Dict[str, Any]) -> bool:
    poi_id = str(payload.get("poi_id") or "")
    fixture_id = str(payload.get("fixture_id") or "")
    pan = int(payload.get("pan") or 0)
    tilt = int(payload.get("tilt") or 0)
    
    if not poi_id or not fixture_id:
        return False

    res = await manager.state_manager.update_fixture_poi_target(fixture_id, poi_id, pan, tilt)
    if res.get("ok"):
        manager.state_manager.canvas_dirty = True
        return True
    return False
