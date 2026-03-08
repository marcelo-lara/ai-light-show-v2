import pytest
import tempfile
import json
from pathlib import Path
import os
from store.pois import PoiDatabase

@pytest.fixture
def temp_pois_file():
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    
    # Initialize with empty list
    with open(path, 'w') as f:
        json.dump([], f)
        
    yield Path(path)
    os.remove(path)

@pytest.mark.asyncio
async def test_poi_crud_persistence(temp_pois_file):
    db = PoiDatabase(temp_pois_file)
    
    # Verify initial empty state
    all_pois = await db.get_all()
    assert len(all_pois) == 0
    
    # 1. Test Create
    new_poi = {
        "id": "test_poi",
        "name": "Test POI",
        "location": {"x": 1, "y": 2, "z": 3},
        "fixtures": {
            "fix1": {"pan": 100, "tilt": 200}
        }
    }
    
    created = await db.create(new_poi)
    assert created["id"] == "test_poi"
    
    # Check file
    with open(temp_pois_file, 'r') as f:
        data = json.load(f)
        assert len(data) == 1
        assert data[0]["id"] == "test_poi"
        
    # 2. Test Update
    update_data = {
        "name": "Updated Test POI",
        "location": {"x": 5, "y": 6, "z": 7}
    }
    
    updated = await db.update("test_poi", update_data)
    assert updated["name"] == "Updated Test POI"
    assert updated["fixtures"]["fix1"]["pan"] == 100  # un-updated fields preserved
    
    # Check file
    with open(temp_pois_file, 'r') as f:
        data = json.load(f)
        assert len(data) == 1
        assert data[0]["name"] == "Updated Test POI"
        assert data[0]["fixtures"]["fix1"]["pan"] == 100
        
    # 3. Test Delete
    deleted = await db.delete("test_poi")
    assert deleted is True
    
    # Check file
    with open(temp_pois_file, 'r') as f:
        data = json.load(f)
        assert len(data) == 0

