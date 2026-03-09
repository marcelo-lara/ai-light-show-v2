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


@pytest.mark.asyncio
async def test_poi_update_fixture_node_add_and_update(temp_pois_file):
    db = PoiDatabase(temp_pois_file)

    await db.create({
        "id": "poi_1",
        "name": "POI 1",
        "location": {"x": 0.1, "y": 0.2, "z": 0.3},
    })

    # Add missing fixtures node and target fixture entry.
    saved = await db.set_fixture_target("poi_1", "fixture_a", {"pan": 111, "tilt": 222})
    assert saved == {"pan": 111, "tilt": 222}

    with open(temp_pois_file, "r") as f:
        data = json.load(f)
    assert data[0]["fixtures"]["fixture_a"]["pan"] == 111
    assert data[0]["fixtures"]["fixture_a"]["tilt"] == 222

    # Update existing fixture entry for same POI.
    saved = await db.set_fixture_target("poi_1", "fixture_a", {"pan": 333, "tilt": 444})
    assert saved == {"pan": 333, "tilt": 444}

    with open(temp_pois_file, "r") as f:
        data = json.load(f)
    assert data[0]["fixtures"]["fixture_a"]["pan"] == 333
    assert data[0]["fixtures"]["fixture_a"]["tilt"] == 444
