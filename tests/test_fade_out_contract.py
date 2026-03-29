import pytest

from tests.fixture_effect_matrix import FIXTURES_PATH, build_state_manager

@pytest.mark.asyncio
async def test_parcan_fade_out_honors_last_channel_status_or_data() -> None:
    state_manager = build_state_manager()
    await state_manager.load_fixtures(FIXTURES_PATH)
    fixture = next(item for item in state_manager.fixtures if item.id == "parcan_l")

    default_universe = bytearray(512)
    default_universe[fixture.absolute_channels["red"] - 1] = 128
    default_universe[fixture.absolute_channels["green"] - 1] = 128
    default_universe[fixture.absolute_channels["blue"] - 1] = 128

    fixture.render_effect(
        default_universe,
        effect="fade_out",
        frame_index=60,
        start_frame=60,
        end_frame=90,
        fps=60,
        data={},
        render_state={},
    )
    assert default_universe[fixture.absolute_channels["red"] - 1] == 128
    
    custom_universe = bytearray(512)
    fixture.render_effect(
        custom_universe,
        effect="fade_out",
        frame_index=60,
        start_frame=60,
        end_frame=90,
        fps=60,
        data={"start_value": {"red": 128}},
        render_state={},
    )
    assert custom_universe[fixture.absolute_channels["red"] - 1] == 128

@pytest.mark.asyncio
async def test_moving_head_fade_out_defaults_to_last_channel_status_and_honors_start_value() -> None:
    state_manager = build_state_manager()
    await state_manager.load_fixtures(FIXTURES_PATH)
    fixture = next(item for item in state_manager.fixtures if item.id == "mini_beam_prism_l")

    default_universe = bytearray(512)
    default_universe[fixture.absolute_channels["dim"] - 1] = 64

    fixture.render_effect(
        default_universe,
        effect="fade_out",
        frame_index=60,
        start_frame=60,
        end_frame=90,
        fps=60,
        data={},
        render_state={},
    )
    assert default_universe[fixture.absolute_channels["dim"] - 1] == 64

    custom_universe = bytearray(512)
    fixture.render_effect(
        custom_universe,
        effect="fade_out",
        frame_index=60,
        start_frame=60,
        end_frame=90,
        fps=60,
        data={"start_value": 0.5},
        render_state={},
    )
    assert custom_universe[fixture.absolute_channels["dim"] - 1] in (127, 128)
