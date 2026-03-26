import pytest

from tests.fixture_effect_matrix import FIXTURES_PATH, build_state_manager


@pytest.mark.asyncio
async def test_parcan_fade_out_defaults_to_full_and_honors_fractional_start() -> None:
    state_manager = build_state_manager()
    await state_manager.load_fixtures(FIXTURES_PATH)
    fixture = next(item for item in state_manager.fixtures if item.id == "parcan_l")

    default_universe = bytearray(512)
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

    assert default_universe[fixture.absolute_channels["red"] - 1] == 255
    assert default_universe[fixture.absolute_channels["green"] - 1] == 255
    assert default_universe[fixture.absolute_channels["blue"] - 1] == 255

    custom_universe = bytearray(512)
    fixture.render_effect(
        custom_universe,
        effect="fade_out",
        frame_index=60,
        start_frame=60,
        end_frame=90,
        fps=60,
        data={"red": 0.5, "green": 0.25, "blue": 1},
        render_state={},
    )

    assert custom_universe[fixture.absolute_channels["red"] - 1] == 128
    assert custom_universe[fixture.absolute_channels["green"] - 1] == 64
    assert custom_universe[fixture.absolute_channels["blue"] - 1] == 255


@pytest.mark.asyncio
async def test_moving_head_fade_out_defaults_to_full_and_honors_fractional_start() -> None:
    state_manager = build_state_manager()
    await state_manager.load_fixtures(FIXTURES_PATH)
    fixture = next(item for item in state_manager.fixtures if item.id == "mini_beam_prism_l")

    default_universe = bytearray(512)
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

    assert default_universe[fixture.absolute_channels["dim"] - 1] == 255

    custom_universe = bytearray(512)
    fixture.render_effect(
        custom_universe,
        effect="fade_out",
        frame_index=60,
        start_frame=60,
        end_frame=90,
        fps=60,
        data={"dim": 0.5},
        render_state={},
    )

    assert custom_universe[fixture.absolute_channels["dim"] - 1] == 128