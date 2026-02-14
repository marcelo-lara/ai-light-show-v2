import math
from pathlib import Path

from backend.store.state import StateManager, FPS
from backend.models.cue import CueSheet, CueEntry
from backend.models.fixtures.parcans.parcan import Parcan
from backend.models.fixtures.moving_heads.moving_head import MovingHead


def test_dmx_canvas_renders_set_channels_and_persists():
    # Arrange: two parcans with blue channels at different indices
    sm = StateManager(Path('.'))
    parcan_l = Parcan(
        id='parcan_l',
        name='ParCan L',
        type='parcan',
        channels={'dim': 1, 'red': 2, 'green': 3, 'blue': 4},
        location={'x': 0.0, 'y': 0, 'z': 0},
    )
    parcan_r = Parcan(
        id='parcan_r',
        name='ParCan R',
        type='parcan',
        channels={'dim': 5, 'red': 6, 'green': 7, 'blue': 8},
        location={'x': 1.0, 'y': 0, 'z': 0},
    )
    sm.fixtures = [parcan_l, parcan_r]

    # Make a short song and cues: left parcan blue at t=0.0, right parcan blue at t=0.5
    sm.song_length_seconds = 1.0
    sm.cue_sheet = CueSheet(
        song_filename='test_song',
        entries=[
            CueEntry(time=0.0, fixture_id='parcan_l', effect='set_channels', data={'channels': {'blue': 255}}),
            CueEntry(time=0.5, fixture_id='parcan_r', effect='set_channels', data={'channels': {'blue': 255}}),
        ],
    )

    # Act: render canvas
    canvas = sm._render_cue_sheet_to_canvas()

    # Compute frame indices
    frame0 = int(round(0.0 * FPS))
    frame_half = int(round(0.5 * FPS))

    # Assert initial frame: left parcan blue on, right off
    view0 = canvas.frame_view(frame0)
    assert view0[4 - 1] == 255  # parcan_l blue (channel 4)
    assert view0[8 - 1] == 0    # parcan_r blue (channel 8)

    # Assert just before the second cue: right parcan still off
    if frame_half > 0:
        view_before = canvas.frame_view(frame_half - 1)
        assert view_before[8 - 1] == 0

    # Assert at and after the second cue: both are on and persist to the end
    view_half = canvas.frame_view(frame_half)
    assert view_half[4 - 1] == 255
    assert view_half[8 - 1] == 255

    view_last = canvas.frame_view(canvas.total_frames - 1)
    assert view_last[4 - 1] == 255
    assert view_last[8 - 1] == 255


def test_dmx_canvas_renders_fade_in_rgb_only_and_persists():
    sm = StateManager(Path('.'))
    parcan = Parcan(
        id='parcan_1',
        name='ParCan 1',
        type='parcan',
        channels={'dim': 1, 'red': 2, 'green': 3, 'blue': 4},
        location={'x': 0.0, 'y': 0, 'z': 0},
    )
    sm.fixtures = [parcan]

    sm.song_length_seconds = 2.0
    sm.cue_sheet = CueSheet(
        song_filename='test_song',
        entries=[
            CueEntry(time=0.0, fixture_id='parcan_1', effect='fade_in', duration=1.0, data={'red': 255}),
        ],
    )

    canvas = sm._render_cue_sheet_to_canvas()

    frame_start = int(round(0.0 * FPS))
    frame_mid = int(round(0.5 * FPS))
    frame_end = int(round(1.0 * FPS))

    # Start: red begins at current value (0)
    view_start = canvas.frame_view(frame_start)
    assert view_start[2 - 1] == 0
    assert view_start[3 - 1] == 0
    assert view_start[4 - 1] == 0

    # Midpoint: roughly half intensity (allow 1 step of rounding)
    view_mid = canvas.frame_view(frame_mid)
    assert 127 <= view_mid[2 - 1] <= 128
    assert view_mid[3 - 1] == 0
    assert view_mid[4 - 1] == 0

    # End: reaches full red
    view_end = canvas.frame_view(frame_end)
    assert view_end[2 - 1] == 255
    assert view_end[3 - 1] == 0
    assert view_end[4 - 1] == 0

    # After end: persists (universe carries forward) until overwritten
    view_after = canvas.frame_view(frame_end + 1)
    assert view_after[2 - 1] == 255


def test_dmx_canvas_renders_full_rgb_and_persists():
    sm = StateManager(Path('.'))
    parcan = Parcan(
        id='parcan_1',
        name='ParCan 1',
        type='parcan',
        channels={'dim': 1, 'red': 2, 'green': 3, 'blue': 4},
        location={'x': 0.0, 'y': 0, 'z': 0},
    )
    sm.fixtures = [parcan]

    sm.song_length_seconds = 1.0
    sm.cue_sheet = CueSheet(
        song_filename='test_song',
        entries=[
            CueEntry(time=0.0, fixture_id='parcan_1', effect='full', duration=0.0, data={'red': 10, 'green': 20, 'blue': 30}),
        ],
    )

    canvas = sm._render_cue_sheet_to_canvas()
    view0 = canvas.frame_view(0)
    assert view0[2 - 1] == 10
    assert view0[3 - 1] == 20
    assert view0[4 - 1] == 30

    view_last = canvas.frame_view(canvas.total_frames - 1)
    assert view_last[2 - 1] == 10
    assert view_last[3 - 1] == 20
    assert view_last[4 - 1] == 30


def test_dmx_canvas_renders_flash_starts_full_and_ends_off():
    sm = StateManager(Path('.'))
    parcan = Parcan(
        id='parcan_1',
        name='ParCan 1',
        type='parcan',
        channels={'dim': 1, 'red': 2, 'green': 3, 'blue': 4},
        location={'x': 0.0, 'y': 0, 'z': 0},
    )
    sm.fixtures = [parcan]

    sm.song_length_seconds = 2.0
    sm.cue_sheet = CueSheet(
        song_filename='test_song',
        entries=[
            CueEntry(time=0.0, fixture_id='parcan_1', effect='flash', duration=1.0, data={}),
        ],
    )

    canvas = sm._render_cue_sheet_to_canvas()
    frame_start = int(round(0.0 * FPS))
    frame_end = int(round(1.0 * FPS))

    view_start = canvas.frame_view(frame_start)
    assert view_start[2 - 1] == 255
    assert view_start[3 - 1] == 255
    assert view_start[4 - 1] == 255

    view_end = canvas.frame_view(frame_end)
    assert view_end[2 - 1] == 0
    assert view_end[3 - 1] == 0
    assert view_end[4 - 1] == 0


def test_dmx_canvas_renders_strobe_rgb_toggles_and_ends_on():
    sm = StateManager(Path('.'))
    parcan = Parcan(
        id='parcan_1',
        name='ParCan 1',
        type='parcan',
        channels={'dim': 1, 'red': 2, 'green': 3, 'blue': 4},
        location={'x': 0.0, 'y': 0, 'z': 0},
    )
    sm.fixtures = [parcan]

    sm.song_length_seconds = 2.0
    sm.cue_sheet = CueSheet(
        song_filename='test_song',
        entries=[
            # Establish a base color.
            CueEntry(time=0.0, fixture_id='parcan_1', effect='set_channels', duration=0.0, data={'channels': {'red': 255, 'green': 0, 'blue': 0}}),
            # Strobe it at 2Hz for 1 second.
            CueEntry(time=0.0, fixture_id='parcan_1', effect='strobe', duration=1.0, data={'rate': 2.0}),
        ],
    )

    canvas = sm._render_cue_sheet_to_canvas()
    start_frame = int(round(0.0 * FPS))
    mid_off_frame = start_frame + 16  # with 2Hz: half-period ~= 15 frames, so frame 16 is "off"
    end_frame = int(round(1.0 * FPS))

    view_start = canvas.frame_view(start_frame)
    assert view_start[2 - 1] == 255

    view_off = canvas.frame_view(mid_off_frame)
    assert view_off[2 - 1] == 0

    # End frame should restore original "on" color and persist after.
    view_end = canvas.frame_view(end_frame)
    assert view_end[2 - 1] == 255
    view_after = canvas.frame_view(end_frame + 1)
    assert view_after[2 - 1] == 255


def test_dmx_canvas_renders_moving_head_move_to_16bit():
    sm = StateManager(Path('.'))
    head = MovingHead(
        id='head_1',
        name='Head 1',
        type='moving_head',
        channels={
            'pan_msb': 1,
            'pan_lsb': 2,
            'tilt_msb': 3,
            'tilt_lsb': 4,
            'dim': 5,
            'shutter': 6,
        },
        location={'x': 0.0, 'y': 0, 'z': 0},
        presets=[],
    )
    sm.fixtures = [head]

    sm.song_length_seconds = 2.0
    sm.cue_sheet = CueSheet(
        song_filename='test_song',
        entries=[
            CueEntry(time=0.0, fixture_id='head_1', effect='move_to', duration=1.0, data={'pan': 0x1234, 'tilt': 0xABCD}),
        ],
    )

    canvas = sm._render_cue_sheet_to_canvas()
    frame_mid = int(round(0.5 * FPS))
    frame_end = int(round(1.0 * FPS))

    view_mid = canvas.frame_view(frame_mid)
    # Pan ~ 0x091A at halfway (allow rounding).
    pan_mid = (int(view_mid[1 - 1]) << 8) | int(view_mid[2 - 1])
    assert 0x0919 <= pan_mid <= 0x091B

    view_end = canvas.frame_view(frame_end)
    pan_end = (int(view_end[1 - 1]) << 8) | int(view_end[2 - 1])
    tilt_end = (int(view_end[3 - 1]) << 8) | int(view_end[4 - 1])
    assert pan_end == 0x1234
    assert tilt_end == 0xABCD


def test_dmx_canvas_renders_moving_head_seek_preset_16bit():
    sm = StateManager(Path('.'))
    head = MovingHead(
        id='head_1',
        name='Head 1',
        type='moving_head',
        channels={
            'pan_msb': 1,
            'pan_lsb': 2,
            'tilt_msb': 3,
            'tilt_lsb': 4,
        },
        location={'x': 0.0, 'y': 0, 'z': 0},
        presets=[
            {'name': 'Piano', 'values': {'pan': 120, 'pan_fine': 35, 'tilt': 20, 'tilt_fine': 11}},
        ],
    )
    sm.fixtures = [head]
    sm.song_length_seconds = 1.0
    sm.cue_sheet = CueSheet(
        song_filename='test_song',
        entries=[
            CueEntry(time=0.0, fixture_id='head_1', effect='seek', duration=0.0, data={'preset': 'Piano'}),
        ],
    )

    canvas = sm._render_cue_sheet_to_canvas()
    view0 = canvas.frame_view(0)
    pan = (int(view0[1 - 1]) << 8) | int(view0[2 - 1])
    tilt = (int(view0[3 - 1]) << 8) | int(view0[4 - 1])
    assert pan == ((120 << 8) | 35)
    assert tilt == ((20 << 8) | 11)


def test_dmx_canvas_renders_moving_head_flash_starts_full_and_ends_off():
    sm = StateManager(Path('.'))
    head = MovingHead(
        id='head_1',
        name='Head 1',
        type='moving_head',
        channels={
            'pan_msb': 1,
            'pan_lsb': 2,
            'tilt_msb': 3,
            'tilt_lsb': 4,
            'dim': 5,
            'shutter': 6,
        },
        location={'x': 0.0, 'y': 0, 'z': 0},
        presets=[],
    )
    sm.fixtures = [head]

    sm.song_length_seconds = 2.0
    sm.cue_sheet = CueSheet(
        song_filename='test_song',
        entries=[
            CueEntry(time=0.0, fixture_id='head_1', effect='flash', duration=1.0, data={}),
        ],
    )

    canvas = sm._render_cue_sheet_to_canvas()
    frame_start = int(round(0.0 * FPS))
    frame_end = int(round(1.0 * FPS))

    view_start = canvas.frame_view(frame_start)
    assert view_start[5 - 1] == 255

    view_end = canvas.frame_view(frame_end)
    assert view_end[5 - 1] == 0


def test_dmx_canvas_renders_moving_head_sweep_peaks_at_preset():
    sm = StateManager(Path('.'))
    head = MovingHead(
        id='head_1',
        name='Head 1',
        type='moving_head',
        channels={
            'pan_msb': 1,
            'pan_lsb': 2,
            'tilt_msb': 3,
            'tilt_lsb': 4,
            'dim': 5,
            'shutter': 6,
        },
        location={'x': 0.0, 'y': 0, 'z': 0},
        presets=[
            {'name': 'Piano', 'values': {'pan': 120, 'pan_fine': 35, 'tilt': 20, 'tilt_fine': 11}},
        ],
    )
    sm.fixtures = [head]

    sm.song_length_seconds = 3.0
    sm.cue_sheet = CueSheet(
        song_filename='test_song',
        entries=[
            # Sweep for 2 seconds across the Piano preset.
            CueEntry(time=0.0, fixture_id='head_1', effect='sweep', duration=2.0, data={'preset': 'Piano', 'span_pan': 1000, 'span_tilt': 0}),
        ],
    )

    canvas = sm._render_cue_sheet_to_canvas()
    frame_start = int(round(0.0 * FPS))
    frame_mid = int(round(1.0 * FPS))
    frame_end = int(round(2.0 * FPS))

    target_pan = (120 << 8) | 35
    target_tilt = (20 << 8) | 11
    start_pan = target_pan - 500
    end_pan = target_pan + 500

    view_start = canvas.frame_view(frame_start)
    pan_start = (int(view_start[1 - 1]) << 8) | int(view_start[2 - 1])
    assert abs(pan_start - start_pan) <= 1
    assert int(view_start[5 - 1]) == 0

    view_mid = canvas.frame_view(frame_mid)
    pan_mid = (int(view_mid[1 - 1]) << 8) | int(view_mid[2 - 1])
    tilt_mid = (int(view_mid[3 - 1]) << 8) | int(view_mid[4 - 1])
    assert abs(pan_mid - target_pan) <= 1
    assert abs(tilt_mid - target_tilt) <= 1
    assert int(view_mid[5 - 1]) == 255
    assert int(view_mid[6 - 1]) == 255

    view_end = canvas.frame_view(frame_end)
    pan_end = (int(view_end[1 - 1]) << 8) | int(view_end[2 - 1])
    assert abs(pan_end - end_pan) <= 1
    assert int(view_end[5 - 1]) == 0


def test_dmx_canvas_renders_moving_head_sweep_center_2s_mid_and_end():
    sm = StateManager(Path('.'))
    head = MovingHead(
        id='head_el150',
        name='Head EL-150',
        type='moving_head',
        channels={
            'pan_msb': 1,
            'pan_lsb': 2,
            'tilt_msb': 3,
            'tilt_lsb': 4,
            'speed': 5,
            'dim': 6,
            'shutter': 7,
        },
        location={'x': 0.4, 'y': 0, 'z': 0},
        presets=[],
    )
    sm.fixtures = [head]

    center_pan = (0 + 65535) // 2
    center_tilt = (70 + 3363) // 2
    span_pan = 1000
    span_tilt = 600
    start_pan = center_pan - span_pan // 2
    start_tilt = center_tilt - span_tilt // 2
    end_pan = center_pan + span_pan // 2
    end_tilt = center_tilt + span_tilt // 2

    sm.song_length_seconds = 3.0
    sm.cue_sheet = CueSheet(
        song_filename='test_song',
        entries=[
            CueEntry(
                time=0.0,
                fixture_id='head_el150',
                effect='sweep',
                duration=2.0,
                data={
                    'pan': center_pan,
                    'tilt': center_tilt,
                    'span_pan': span_pan,
                    'span_tilt': span_tilt,
                },
            ),
        ],
    )

    canvas = sm._render_cue_sheet_to_canvas()
    frame_start = int(round(0.0 * FPS))
    frame_mid = int(round(1.0 * FPS))
    frame_end = int(round(2.0 * FPS))

    view_start = canvas.frame_view(frame_start)
    pan_start = (int(view_start[1 - 1]) << 8) | int(view_start[2 - 1])
    tilt_start = (int(view_start[3 - 1]) << 8) | int(view_start[4 - 1])
    assert abs(pan_start - start_pan) <= 1
    assert abs(tilt_start - start_tilt) <= 1
    assert int(view_start[6 - 1]) == 0

    view_mid = canvas.frame_view(frame_mid)
    pan_mid = (int(view_mid[1 - 1]) << 8) | int(view_mid[2 - 1])
    tilt_mid = (int(view_mid[3 - 1]) << 8) | int(view_mid[4 - 1])
    assert abs(pan_mid - center_pan) <= 1
    assert abs(tilt_mid - center_tilt) <= 1
    assert int(view_mid[6 - 1]) == 255

    view_end = canvas.frame_view(frame_end)
    pan_end = (int(view_end[1 - 1]) << 8) | int(view_end[2 - 1])
    tilt_end = (int(view_end[3 - 1]) << 8) | int(view_end[4 - 1])
    assert abs(pan_end - end_pan) <= 1
    assert abs(tilt_end - end_tilt) <= 1
    assert int(view_end[6 - 1]) == 0
