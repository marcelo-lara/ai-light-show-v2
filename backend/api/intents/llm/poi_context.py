from __future__ import annotations

from typing import Any, Dict, List


async def build_poi_inventory_payload(manager) -> Dict[str, Any]:
    pois = await manager.state_manager.get_pois()
    items: List[Dict[str, Any]] = []

    for poi in pois:
        if not isinstance(poi, dict):
            continue
        fixture_targets = poi.get("fixtures") or {}
        fixture_ids = sorted(str(fixture_id) for fixture_id in fixture_targets.keys())
        items.append(
            {
                "id": str(poi.get("id") or ""),
                "name": str(poi.get("name") or poi.get("id") or ""),
                "fixture_ids": fixture_ids,
                "fixture_target_count": len(fixture_ids),
            }
        )

    items.sort(key=lambda item: item["id"])
    answer = "Available POIs: " + ", ".join(item["id"] for item in items) + "." if items else "No POIs are available."
    return {"pois": items, "answer": answer}