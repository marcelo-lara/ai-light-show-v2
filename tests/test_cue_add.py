import pytest
from pathlib import Path
from backend.store.state import StateManager
from backend.models.cue import CueSheet


@pytest.fixture
def workspace_root():
    return Path("/home/darkangel/ai-light-show-v2")


@pytest.fixture
def state_manager(workspace_root):
    backend_path = workspace_root / "backend"
    return StateManager(backend_path=backend_path)


@pytest.mark.asyncio
async def test_add_effect_cue_entry_valid(state_manager, workspace_root):
    """Test adding a valid effect cue entry."""
    # Load fixtures
    fixtures_json = workspace_root / "backend" / "fixtures" / "fixtures.json"
    await state_manager.load_fixtures(fixtures_json)

    # Initialize empty cue sheet
    state_manager.cue_sheet = CueSheet(song_filename="test_cue_add", entries=[])

    # Add a valid flash effect to parcan_l
    result = await state_manager.add_effect_cue_entry(
        time=5.0,
        fixture_id="parcan_l",
        effect="flash",
        duration=0.5,
        data={},
    )

    assert result["ok"] is True
    assert "entry" in result
    assert result["entry"]["time"] == 5.0
    assert result["entry"]["fixture_id"] == "parcan_l"
    assert result["entry"]["effect"] == "flash"
    assert result["entry"]["duration"] == 0.5

    # Verify cue was added to sheet
    assert len(state_manager.cue_sheet.entries) == 1


@pytest.mark.asyncio
async def test_add_effect_cue_entry_invalid_fixture(state_manager, workspace_root):
    """Test adding cue with non-existent fixture fails."""
    fixtures_json = workspace_root / "backend" / "fixtures" / "fixtures.json"
    await state_manager.load_fixtures(fixtures_json)

    state_manager.cue_sheet = CueSheet(song_filename="test_cue_add", entries=[])

    result = await state_manager.add_effect_cue_entry(
        time=1.0,
        fixture_id="nonexistent_fixture",
        effect="flash",
        duration=0.5,
        data={},
    )

    assert result["ok"] is False
    assert result["reason"] == "fixture_not_found"


@pytest.mark.asyncio
async def test_add_effect_cue_entry_invalid_effect(state_manager, workspace_root):
    """Test adding cue with unsupported effect fails."""
    fixtures_json = workspace_root / "backend" / "fixtures" / "fixtures.json"
    await state_manager.load_fixtures(fixtures_json)

    state_manager.cue_sheet = CueSheet(song_filename="test_cue_add", entries=[])

    # Try to add sweep (moving_head effect) to a parcan
    result = await state_manager.add_effect_cue_entry(
        time=1.0,
        fixture_id="parcan_l",
        effect="sweep",
        duration=1.0,
        data={},
    )

    assert result["ok"] is False
    assert result["reason"] == "effect_not_supported"
    assert "supported" in result


@pytest.mark.asyncio
async def test_add_effect_cue_entry_no_cue_sheet(state_manager, workspace_root):
    """Test adding cue without loaded cue sheet fails."""
    fixtures_json = workspace_root / "backend" / "fixtures" / "fixtures.json"
    await state_manager.load_fixtures(fixtures_json)

    # No cue sheet loaded
    state_manager.cue_sheet = None

    result = await state_manager.add_effect_cue_entry(
        time=1.0,
        fixture_id="parcan_l",
        effect="flash",
        duration=0.5,
        data={},
    )

    assert result["ok"] is False
    assert result["reason"] == "no_cue_sheet"


@pytest.mark.asyncio
async def test_add_effect_cue_entry_with_params(state_manager, workspace_root):
    """Test adding cue with effect parameters."""
    fixtures_json = workspace_root / "backend" / "fixtures" / "fixtures.json"
    await state_manager.load_fixtures(fixtures_json)

    state_manager.cue_sheet = CueSheet(song_filename="test_cue_add", entries=[])

    result = await state_manager.add_effect_cue_entry(
        time=2.0,
        fixture_id="parcan_l",
        effect="strobe",
        duration=2.0,
        data={"rate": 15},
    )

    assert result["ok"] is True
    assert result["entry"]["data"] == {"rate": 15}


@pytest.mark.asyncio
async def test_get_cue_entries(state_manager, workspace_root):
    """Test get_cue_entries returns list of dicts."""
    fixtures_json = workspace_root / "backend" / "fixtures" / "fixtures.json"
    await state_manager.load_fixtures(fixtures_json)

    state_manager.cue_sheet = CueSheet(song_filename="test_cue_add", entries=[])

    # Add two cues
    await state_manager.add_effect_cue_entry(
        time=1.0, fixture_id="parcan_l", effect="flash", duration=0.5, data={}
    )
    await state_manager.add_effect_cue_entry(
        time=3.0, fixture_id="parcan_l", effect="strobe", duration=1.0, data={"rate": 10}
    )

    entries = state_manager.get_cue_entries()

    assert len(entries) == 2
    assert entries[0]["time"] == 1.0
    assert entries[1]["time"] == 3.0
    assert isinstance(entries[0], dict)
