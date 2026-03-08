from typing import Any, Dict

async def create_poi(manager, payload: Dict[str, Any]) -> bool:
    try:
        await manager.state_manager.poi_db.create(payload)
        return True
    except Exception as e:
        print(f"Error creating POI: {e}")
        return False
