import pytest
import os
import json
from pathlib import Path
from backend.store.state import StateManager
from backend.models.fixtures.moving_heads.moving_head import MovingHead
from backend.models.fixtures.parcans.parcan import Parcan
from backend.models.fixtures.fixture import Fixture as BaseFixture

@pytest.fixture
def workspace_root():
    return Path("/home/darkangel/ai-light-show-v2")

@pytest.fixture
def state_manager(workspace_root):
    backend_path = workspace_root / "backend"
    return StateManager(backend_path=backend_path)

@pytest.mark.asyncio
async def test_fixture_loading(state_manager, workspace_root):
    fixtures_json = workspace_root / "backend" / "fixtures" / "fixtures.json"
    await state_manager.load_fixtures(fixtures_json)
    
    assert len(state_manager.fixtures) > 0
    
    # Use string comparison for types to avoid module path mismatch issues
    moving_heads = [f for f in state_manager.fixtures if "MovingHead" in str(type(f))]
    parcans = [f for f in state_manager.fixtures if "Parcan" in str(type(f))]
    
    assert len(moving_heads) > 0
    assert len(parcans) > 0
    
    # Verify a moving head (mini_beam_prism_l)
    mh = next(f for f in moving_heads if f.id == "mini_beam_prism_l")
    assert mh.base_channel == 42
    assert "pan" in mh.meta_channels
    assert mh.meta_channels["pan"].kind == "u16"
    
    # Verify absolute channel calculation
    # dim is offset 5 for mini_beam_prism
    assert mh.absolute_channels["dim"] == 42 + 5
    
    # Verify Arming (Parcan Dimmer arm is 255)
    pl = next(f for f in parcans if f.id == "parcan_l")
    dim_ch = pl.absolute_channels["dim"]
    assert state_manager.editor_universe[dim_ch - 1] == 255



@pytest.mark.asyncio
async def test_absolute_channels(state_manager, workspace_root):
    fixtures_json = workspace_root / "backend" / "fixtures" / "fixtures.json"
    await state_manager.load_fixtures(fixtures_json)
    
    for fixture in state_manager.fixtures:
        for name, abs_ch in fixture.absolute_channels.items():
            assert abs_ch == fixture.base_channel + fixture.channels[name]
