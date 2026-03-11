from typing import Any, Dict

async def update_poi(manager, payload: Dict[str, Any]) -> bool:
    poi_id = payload.get("id")
    if not poi_id:
        return False
    try:
        updated = await manager.state_manager.poi_db.update(poi_id, payload)
        return bool(updated)
    except Exception as e:
        print(f"Error updating POI: {e}")
        return False
