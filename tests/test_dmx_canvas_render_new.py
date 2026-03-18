import pytest
import os
import json
from pathlib import Path
from types import SimpleNamespace
from backend.store.state import StateManager
from backend.models.fixtures.moving_heads.moving_head import MovingHead
from backend.models.fixtures.parcans.parcan import Parcan
from backend.models.cues import CueSheet

@pytest.fixture
def workspace_root():
    return Path("/home/darkangel/ai-light-show-v2")

@pytest.fixture
def state_manager(workspace_root):
    backend_path = workspace_root / "backend"
    return StateManager(backend_path=backend_path)

@pytest.mark.asyncio
async def test_dmx_canvas_render_with_templates(state_manager, workspace_root):
    # Setup: Load fixtures
    fixtures_json = workspace_root / "backend" / "fixtures" / "fixtures.json"
    await state_manager.load_fixtures(fixtures_json)
    
    # Setup: Mock a song and cue sheet
    # We want to test 'set_channels' and 'flash' on a Parcan (parcan_l, base 1)
    # and 'move_to' on a MovingHead (mini_beam_prism_l, base 42)
    
    parcan_id = "parcan_l" # base 16 according to fixtures.json
    mh_id = "mini_beam_prism_l" # base 42 according to fixtures.json

    cues = [
        {
            "time": 1.0, # Start at 1s
            "fixture_id": parcan_id,
            "name": "set_red",
            "effect": "set_channels",
            "duration": 0,
            "data": {"channels": {"red": 255}}
        },
        {
            "time": 2.0, # at 2s
            "fixture_id": mh_id,
            "name": "move_pan",
            "effect": "move_to",
            "duration": 1.0, # 1 second move
            "data": {"pan": 65535, "tilt": 0} # tilt 0
        }
    ]
    
    # Save these to a temp cue file
    temp_cue_path = workspace_root / "backend" / "cues" / "test_render.json"
    temp_cue_path.parent.mkdir(parents=True, exist_ok=True)
    with open(temp_cue_path, "w") as f:
        json.dump(cues, f)
    
    # Load into state manager
    from backend.models.cues import CueSheet
    with open(temp_cue_path, "r") as f:
        state_manager.cue_sheet = CueSheet(song_filename="test_render", entries=json.load(f))
    
    # Precompute canvas (using 60fps)
    # Mock song length
    state_manager.song_length_seconds = 5.0
    
    # Render!
    state_manager.canvas = state_manager._render_cue_sheet_to_canvas()
    
    # Verification
    # 1. Check parcan_l at 1.1s (frame 66). Red should be 255.
    # red is offset 0, so channel base_channel + 0 = 16 + 0 = 16.
    # DMX channel 16 is index 15.
    frame_66 = state_manager.canvas.frame_view(66)
    assert frame_66[15] == 255
    
    # 2. Check moving head at 2.5s (halfway through 1s move). 
    # start_pan likely 0 (default), target 65535. Halfway => 32768.
    # pan_msb is offset 0 (ch 42), pan_lsb is offset 1 (ch 43).
    # 32768 => MSB 128, LSB 0.
    frame_150 = state_manager.canvas.frame_view(150) # 2.5 * 60 = 150
    # Add some tolerance for floating point timing
    assert 120 <= frame_150[41] <= 135 # 1-based channel 42 is index 41
    
    # Cleanup
    if temp_cue_path.exists():
        temp_cue_path.unlink()


@pytest.mark.asyncio
async def test_dmx_canvas_render_with_chaser_entry(state_manager, workspace_root):
    fixtures_json = workspace_root / "backend" / "fixtures" / "fixtures.json"
    await state_manager.load_fixtures(fixtures_json)
    state_manager.load_chasers()
    state_manager.current_song = SimpleNamespace(meta=SimpleNamespace(bpm=120.0))
    state_manager.song_length_seconds = 5.0
    state_manager.cue_sheet = CueSheet(
        song_filename="test_render",
        entries=[{"time": 0.0, "chaser_id": "blue_parcan_chase", "data": {"repetitions": 1}}],
    )

    state_manager.canvas = state_manager._render_cue_sheet_to_canvas()

    first_flash = state_manager.canvas.frame_view(0)
    second_flash = state_manager.canvas.frame_view(30)

    assert first_flash[30] == 255
    assert second_flash[18] == 255
