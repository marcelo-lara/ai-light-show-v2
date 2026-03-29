import json
import asyncio
from copy import deepcopy
from pathlib import Path
from typing import List, Dict, Any, Optional

class PoiDatabase:
    _instance: Optional['PoiDatabase'] = None

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.lock = asyncio.Lock()
        self.pois: List[Dict[str, Any]] = []
        self._load_sync()
        PoiDatabase._instance = self

    def _load_sync(self):
        if self.filepath.exists():
            with open(self.filepath, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    self.pois = [item for item in data if isinstance(item, dict)]
        else:
            self.pois = []

    async def reload(self):
        async with self.lock:
            self._load_sync()

    def _save_unlocked(self) -> None:
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, 'w') as f:
            json.dump(self.pois, f, indent=4)

    async def save(self):
        async with self.lock:
            self._save_unlocked()

    async def get_all(self) -> List[Dict[str, Any]]:
        async with self.lock:
            return deepcopy(self.pois)

    async def get(self, poi_id: str) -> Optional[Dict[str, Any]]:
        async with self.lock:
            for poi in self.pois:
                if poi.get("id") == poi_id:
                    return deepcopy(poi)
            return None
            
    async def create(self, poi_data: Dict[str, Any]) -> Dict[str, Any]:
        async with self.lock:
            poi_id = poi_data.get("id")
            if not poi_id:
                raise ValueError("POI must have an id")
            for poi in self.pois:
                if poi.get("id") == poi_id:
                    raise ValueError(f"POI with id {poi_id} already exists")
            self.pois.append(poi_data)
            self._save_unlocked()
        return poi_data

    async def update(self, poi_id: str, poi_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        async with self.lock:
            for i, poi in enumerate(self.pois):
                if poi.get("id") == poi_id:
                    self.pois[i] = {**poi, **poi_data, "id": poi_id}
                    updated = self.pois[i]
                    self._save_unlocked()
                    break
            else:
                return None
        return updated

    async def delete(self, poi_id: str) -> bool:
        async with self.lock:
            initial_len = len(self.pois)
            self.pois = [p for p in self.pois if p.get("id") != poi_id]
            if len(self.pois) == initial_len:
                return False
            self._save_unlocked()
        return True

    def get_fixture_target_sync(self, poi_id: str, fixture_id: str) -> Optional[Dict[str, Any]]:
        for poi in self.pois:
            if str(poi.get("id")).strip().lower() == str(poi_id).strip().lower():
                fixtures = poi.get("fixtures", {})
                if not isinstance(fixtures, dict):
                    return None
                
                for f_id, f_data in fixtures.items():
                    if str(f_id).strip().lower() == str(fixture_id).strip().lower():
                        return f_data
        return None

    async def set_fixture_target(self, poi_id: str, fixture_id: str, channels: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        async with self.lock:
            for poi in self.pois:
                if str(poi.get("id")).strip().lower() == str(poi_id).strip().lower():
                    fixtures = poi.get("fixtures", {})
                    if not isinstance(fixtures, dict) or "fixtures" not in poi:
                        fixtures = {}
                        poi["fixtures"] = fixtures
                    fixtures[fixture_id] = channels
                    self._save_unlocked()
                    return channels
        return None

    @classmethod
    def get_instance(cls) -> Optional['PoiDatabase']:
        return cls._instance


# Compatibility alias while callers migrate.
PoiStore = PoiDatabase
