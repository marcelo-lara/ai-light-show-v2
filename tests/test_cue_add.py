import pytest
from pathlib import Path
from backend.store.state import StateManager
from backend.models.cues import CueSheet, load_cue_sheet


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


@pytest.mark.asyncio
async def test_add_chaser_cue_entry_valid(state_manager, workspace_root):
    fixtures_json = workspace_root / "backend" / "fixtures" / "fixtures.json"
    await state_manager.load_fixtures(fixtures_json)
    state_manager.load_chasers()

    state_manager.cue_sheet = CueSheet(song_filename="test_cue_add", entries=[])

    result = await state_manager.add_chaser_cue_entry(
        time=1.36,
        chaser_id="blue_parcan_chase",
        data={"repetitions": 2},
    )

    assert result["ok"] is True
    assert result["entry"]["chaser_id"] == "blue_parcan_chase"
    assert result["entry"]["data"] == {"repetitions": 2}


@pytest.mark.asyncio
async def test_add_effect_cue_entry_deduplicates_within_100ms(state_manager, workspace_root):
    fixtures_json = workspace_root / "backend" / "fixtures" / "fixtures.json"
    await state_manager.load_fixtures(fixtures_json)

    state_manager.cue_sheet = CueSheet(song_filename="test_cue_add", entries=[])

    first = await state_manager.add_effect_cue_entry(
        time=5.0,
        fixture_id="parcan_l",
        effect="flash",
        duration=0.5,
        data={},
    )
    second = await state_manager.add_effect_cue_entry(
        time=5.05,
        fixture_id="parcan_l",
        effect="flash",
        duration=1.25,
        data={"speed": 2},
    )

    assert first["ok"] is True
    assert second["ok"] is True
    assert len(state_manager.cue_sheet.entries) == 1
    stored = state_manager.cue_sheet.entries[0]
    assert stored.time == 5.05
    assert stored.duration == 1.25
    assert stored.data == {"speed": 2}


@pytest.mark.asyncio
async def test_add_chaser_cue_entry_deduplicates_within_100ms(state_manager, workspace_root):
    fixtures_json = workspace_root / "backend" / "fixtures" / "fixtures.json"
    await state_manager.load_fixtures(fixtures_json)
    state_manager.load_chasers()

    state_manager.cue_sheet = CueSheet(song_filename="test_cue_add", entries=[])

    first = await state_manager.add_chaser_cue_entry(
        time=1.36,
        chaser_id="blue_parcan_chase",
        data={"repetitions": 2},
    )
    second = await state_manager.add_chaser_cue_entry(
        time=1.41,
        chaser_id="blue_parcan_chase",
        data={"repetitions": 4},
    )

    assert first["ok"] is True
    assert second["ok"] is True
    assert len(state_manager.cue_sheet.entries) == 1
    stored = state_manager.cue_sheet.entries[0]
    assert stored.chaser_id == "blue_parcan_chase"
    assert stored.time == 1.41
    assert stored.data == {"repetitions": 4}


@pytest.mark.asyncio
async def test_replace_cue_sheet_entries_deduplicates_within_100ms(state_manager, workspace_root):
    fixtures_json = workspace_root / "backend" / "fixtures" / "fixtures.json"
    await state_manager.load_fixtures(fixtures_json)

    state_manager.cue_sheet = CueSheet(song_filename="test_cue_add", entries=[])

    result = await state_manager.replace_cue_sheet_entries([
        {"time": 2.0, "fixture_id": "parcan_l", "effect": "flash", "duration": 0.5, "data": {}},
        {"time": 2.08, "fixture_id": "parcan_l", "effect": "flash", "duration": 1.0, "data": {"speed": 3}},
        {"time": 2.2, "fixture_id": "parcan_l", "effect": "flash", "duration": 0.25, "data": {}},
    ])

    assert result["ok"] is True
    assert result["count"] == 2
    assert result["entries"][0]["time"] == 2.08
    assert result["entries"][0]["duration"] == 1.0
    assert result["entries"][1]["time"] == 2.2


def test_load_mixed_cue_sheet_real_file(workspace_root):
    cue_sheet = load_cue_sheet(workspace_root / "backend" / "cues", "Yonaka - Seize the Power")
    assert any(getattr(entry, "chaser_id", None) == "blue_parcan_chase" for entry in cue_sheet.entries)
    assert any(getattr(entry, "effect", None) == "flash" for entry in cue_sheet.entries)


@pytest.mark.asyncio
async def test_update_cue_entry(state_manager, workspace_root):
    fixtures_json = workspace_root / "backend" / "fixtures" / "fixtures.json"
    await state_manager.load_fixtures(fixtures_json)

    state_manager.cue_sheet = CueSheet(song_filename="test_cue_add", entries=[])
    await state_manager.add_effect_cue_entry(
        time=1.0, fixture_id="parcan_l", effect="flash", duration=0.5, data={}
    )

    result = await state_manager.update_cue_entry(0, {"duration": 1.25, "name": "updated"})

    assert result["ok"] is True
    assert result["entry"]["duration"] == 1.25
    assert result["entry"]["name"] == "updated"


@pytest.mark.asyncio
async def test_delete_cue_entry(state_manager, workspace_root):
    fixtures_json = workspace_root / "backend" / "fixtures" / "fixtures.json"
    await state_manager.load_fixtures(fixtures_json)

    state_manager.cue_sheet = CueSheet(song_filename="test_cue_add", entries=[])
    await state_manager.add_effect_cue_entry(
        time=1.0, fixture_id="parcan_l", effect="flash", duration=0.5, data={}
    )

    result = await state_manager.delete_cue_entry(0)

    assert result["ok"] is True
    assert result["entry"]["effect"] == "flash"
    assert len(state_manager.cue_sheet.entries) == 0
