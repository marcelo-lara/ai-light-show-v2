import pytest
import os
import json
import shutil
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from backend.store.state import StateManager
from backend.models.fixtures.moving_heads.moving_head import MovingHead
from backend.models.fixtures.parcans.parcan import Parcan
from backend.models.cues import CueSheet
from backend.store.dmx_canvas import DMXCanvas
from backend.store.services.canvas_debug import build_named_canvas_binary_path, build_show_name, dump_canvas_binary

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
    
    # Precompute canvas (using 50fps)
    # Mock song length
    state_manager.song_length_seconds = 5.0
    
    # Render!
    state_manager.canvas = state_manager._render_cue_sheet_to_canvas()
    
    # Verification
    # 1. Check parcan_l at 1.1s (frame 66). Red should be 255.
    # red is offset 0, so channel base_channel + 0 = 16 + 0 = 16.
    # DMX channel 16 is index 15.
    frame_55 = state_manager.canvas.frame_view(55)
    assert frame_55[15] == 255
    
    # 2. Check moving head at 2.5s (halfway through 1s move). 
    # start_pan likely 0 (default), target 65535. Halfway => 32768.
    # pan_msb is offset 0 (ch 42), pan_lsb is offset 1 (ch 43).
    # 32768 => MSB 128, LSB 0.
    frame_125 = state_manager.canvas.frame_view(125) # 2.5 * 50 = 125
    # Add some tolerance for floating point timing
    assert 120 <= frame_125[41] <= 135 # 1-based channel 42 is index 41
    
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


def test_dump_canvas_binary_writes_spec_file_and_overwrites_same_day(tmp_path):
    backend_path = tmp_path / "backend"
    backend_path.mkdir(parents=True)

    canvas = DMXCanvas.allocate(fps=60, total_frames=2)
    first_frame = bytearray(512)
    first_frame[0] = 10
    first_frame[1] = 20
    second_frame = bytearray(512)
    second_frame[0] = 99
    canvas.set_frame(0, first_frame)
    canvas.set_frame(1, second_frame)

    show_date = date(2026, 4, 26)
    output_path = dump_canvas_binary(
        backend_path=backend_path,
        song_filename="demo-song",
        canvas=canvas,
        show_date=show_date,
    )

    assert output_path is not None
    assert output_path == build_named_canvas_binary_path(
        backend_path=backend_path,
        song_filename="demo-song",
        show_date=show_date,
    )
    assert output_path.name == "demo-song.show_20260426.dmx"
    assert build_show_name(show_date) == "show_20260426"

    initial_bytes = output_path.read_bytes()
    assert len(initial_bytes) == 32 + (2 * 516)
    assert initial_bytes[0:4] == b"DMXP"
    assert int.from_bytes(initial_bytes[4:6], "little") == 1
    assert int.from_bytes(initial_bytes[6:8], "little") == 1
    assert int.from_bytes(initial_bytes[8:12], "little") == 2
    assert int.from_bytes(initial_bytes[12:16], "little") == 60
    assert int.from_bytes(initial_bytes[32:36], "little") == 0
    assert initial_bytes[36] == 10
    assert initial_bytes[37] == 20
    assert int.from_bytes(initial_bytes[548:552], "little") == 17
    assert initial_bytes[552] == 99

    updated_frame = bytearray(512)
    updated_frame[0] = 7
    canvas.set_frame(0, updated_frame)
    rewritten_path = dump_canvas_binary(
        backend_path=backend_path,
        song_filename="demo-song",
        canvas=canvas,
        show_date=show_date,
    )

    assert rewritten_path == output_path
    rewritten_bytes = output_path.read_bytes()
    assert rewritten_bytes[36] == 7


@pytest.mark.asyncio
async def test_rerender_dmx_canvas_writes_binary_show_in_data_shows(tmp_path: Path):
    workspace_root = Path(__file__).resolve().parents[1]
    source_backend = workspace_root / "backend"
    backend_path = tmp_path / "backend"
    fixtures_dir = backend_path / "fixtures"
    fixtures_dir.mkdir(parents=True)
    shutil.copytree(source_backend / "fixtures", fixtures_dir, dirs_exist_ok=True)
    (backend_path / "chasers").mkdir(parents=True, exist_ok=True)

    songs_path = tmp_path / "songs"
    cues_path = tmp_path / "cues"
    meta_path = tmp_path / "meta"
    songs_path.mkdir()
    cues_path.mkdir()
    meta_path.mkdir()

    song_name = "alpha-song"
    (songs_path / f"{song_name}.mp3").write_bytes(b"")
    (cues_path / f"{song_name}.json").write_text(
        json.dumps(
            [
                {
                    "time": 0.0,
                    "fixture_id": "parcan_l",
                    "effect": "set_channels",
                    "duration": 0.0,
                    "data": {"channels": {"red": 255}},
                }
            ]
        )
    )

    state_manager = StateManager(backend_path, songs_path, cues_path, meta_path)
    await state_manager.load_fixtures(backend_path / "fixtures" / "fixtures.json")
    await state_manager.load_song(song_name)

    result = await state_manager.rerender_dmx_canvas()

    assert result["ok"] is True
    assert result["song"] == song_name
    assert result["show_name"] == build_show_name()
    assert result["dmx_binary_path"].endswith(f"{song_name}.{build_show_name()}.dmx")
    binary_path = Path(result["dmx_binary_path"])
    assert binary_path.exists()
    assert binary_path.parent == tmp_path / "data" / "shows"
    assert binary_path.read_bytes()[0:4] == b"DMXP"
