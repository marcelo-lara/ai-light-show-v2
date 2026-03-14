# pyright: reportAttributeAccessIssue=false

import json
from pathlib import Path
from typing import Any, Dict, List

from store.dmx_canvas import DMX_CHANNELS
from store.services.fixture_loader import load_fixtures_from_path


class StateCoreFixtureStoreMixin:
    async def load_fixtures(self, fixtures_path: Path):
        async with self.lock:
            self.fixtures_path = Path(fixtures_path)
            fixtures, max_used_channel = load_fixtures_from_path(self.fixtures_path)
            self.fixtures = fixtures
            self.max_used_channel = max_used_channel
            self.editor_universe = bytearray(DMX_CHANNELS)
            self.output_universe = bytearray(DMX_CHANNELS)
            self._apply_arm(self.editor_universe)
            self._apply_arm(self.output_universe)

    @property
    def pois(self) -> List[Dict[str, Any]]:
        return self.poi_db.pois

    async def load_pois(self, pois_path: Path):
        self.poi_db.filepath = pois_path
        await self.poi_db.reload()

    async def get_pois(self) -> List[Dict[str, Any]]:
        return await self.poi_db.get_all()

    async def save_fixtures(self) -> None:
        if not self.fixtures_path:
            raise RuntimeError("fixtures_path_not_set")

        fixtures_payload = [fixture.dict() for fixture in self.fixtures]
        self.fixtures_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.fixtures_path, "w") as f:
            json.dump(fixtures_payload, f, indent=2)

    async def update_fixture_poi_target(
        self,
        fixture_id: str,
        poi_id: str,
        pan: int,
        tilt: int,
    ) -> Dict[str, Any]:
        normalized_poi_id = str(poi_id or "").strip()
        if not normalized_poi_id:
            return {"ok": False, "reason": "invalid_poi_id"}

        target_poi = await self.poi_db.get(normalized_poi_id)
        if not target_poi:
            return {"ok": False, "reason": "poi_not_found"}

        pan_u16 = max(0, min(65535, int(pan)))
        tilt_u16 = max(0, min(65535, int(tilt)))
        saved = await self.poi_db.set_fixture_target(
            normalized_poi_id,
            str(fixture_id),
            {"pan": pan_u16, "tilt": tilt_u16},
        )
        if not saved:
            return {"ok": False, "reason": "persist_failed"}

        self.canvas_dirty = True
        return {
            "ok": True,
            "fixture_id": fixture_id,
            "poi_id": normalized_poi_id,
            "values": {"pan": pan_u16, "tilt": tilt_u16},
        }
