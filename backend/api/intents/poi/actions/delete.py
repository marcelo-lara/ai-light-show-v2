from typing import Any, Dict

async def delete_poi(manager, payload: Dict[str, Any]) -> bool:
    poi_id = payload.get("id")
    if not poi_id:
        return False
    try:
        return await manager.state_manager.poi_db.delete(poi_id)
    except Exception as e:
        print(f"Error deleting POI: {e}")
        return False
