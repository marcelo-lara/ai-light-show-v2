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


def test_dmx_canvas_renders_moving_head_sweep_poi_midpoint_and_opposite():
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
        poi_targets={
            'piano': {'pan': 30720, 'tilt': 4608},
            'table': {'pan': 28672, 'tilt': 4096},
        },
    )
    sm.fixtures = [head]

    sm.song_length_seconds = 3.0
    sm.cue_sheet = CueSheet(
        song_filename='test_song',
        entries=[
            CueEntry(
                time=0.0,
                fixture_id='head_1',
                effect='sweep',
                duration=2.0,
                data={
                    'subject_POI': 'piano',
                    'start_POI': 'table',
                    'duration': 2.0,
                    'max_dim': 1.0,
                    'easing': 0.0,
                },
            ),
        ],
    )

    canvas = sm._render_cue_sheet_to_canvas()
    frame_start = int(round(0.0 * FPS))
    frame_mid = int(round(1.0 * FPS))
    frame_end = int(round(2.0 * FPS))

    start_pan = 28672
    start_tilt = 4096
    target_pan = 30720
    target_tilt = 4608
    opposite_pan = 32768
    opposite_tilt = 5120

    view_start = canvas.frame_view(frame_start)
    pan_start = (int(view_start[1 - 1]) << 8) | int(view_start[2 - 1])
    tilt_start = (int(view_start[3 - 1]) << 8) | int(view_start[4 - 1])
    assert abs(pan_start - start_pan) <= 1
    assert abs(tilt_start - start_tilt) <= 1
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
    tilt_end = (int(view_end[3 - 1]) << 8) | int(view_end[4 - 1])
    assert abs(pan_end - opposite_pan) <= 1
    assert abs(tilt_end - opposite_tilt) <= 1
    assert int(view_end[5 - 1]) == 0


def test_dmx_canvas_renders_moving_head_sweep_with_easing_slows_start():
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
        poi_targets={
            'subject': {'pan': 32768, 'tilt': 16384},
            'start': {'pan': 22768, 'tilt': 15384},
        },
    )
    sm.fixtures = [head]

    start_pan = 22768
    start_tilt = 15384
    subject_pan = 32768
    subject_tilt = 16384
    opposite_pan = 42768
    opposite_tilt = 17384

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
                    'subject_POI': 'subject',
                    'start_POI': 'start',
                    'duration': 2.0,
                    'max_dim': 0.5,
                    'easing': 0.5,
                },
            ),
        ],
    )

    canvas = sm._render_cue_sheet_to_canvas()
    frame_start = int(round(0.0 * FPS))
    frame_quarter = int(round(0.25 * FPS))
    frame_mid = int(round(1.0 * FPS))
    frame_end = int(round(2.0 * FPS))

    view_start = canvas.frame_view(frame_start)
    pan_start = (int(view_start[1 - 1]) << 8) | int(view_start[2 - 1])
    tilt_start = (int(view_start[3 - 1]) << 8) | int(view_start[4 - 1])
    assert abs(pan_start - start_pan) <= 1
    assert abs(tilt_start - start_tilt) <= 1
    assert int(view_start[6 - 1]) == 0

    view_quarter = canvas.frame_view(frame_quarter)
    pan_quarter = (int(view_quarter[1 - 1]) << 8) | int(view_quarter[2 - 1])
    linear_halfway_pan = start_pan + int(round((subject_pan - start_pan) * 0.5))
    assert pan_quarter < linear_halfway_pan

    view_mid = canvas.frame_view(frame_mid)
    pan_mid = (int(view_mid[1 - 1]) << 8) | int(view_mid[2 - 1])
    tilt_mid = (int(view_mid[3 - 1]) << 8) | int(view_mid[4 - 1])
    assert abs(pan_mid - subject_pan) <= 1
    assert abs(tilt_mid - subject_tilt) <= 1
    assert int(view_mid[6 - 1]) == 128

    view_end = canvas.frame_view(frame_end)
    pan_end = (int(view_end[1 - 1]) << 8) | int(view_end[2 - 1])
    tilt_end = (int(view_end[3 - 1]) << 8) | int(view_end[4 - 1])
    assert abs(pan_end - opposite_pan) <= 1
    assert abs(tilt_end - opposite_tilt) <= 1
    assert int(view_end[6 - 1]) == 0


def test_dmx_canvas_renders_moving_head_sweep_ref_to_table_to_ref_1_1_0_soft_3s_with_dim_easing():
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
            'dim': 6,
            'shutter': 7,
        },
        location={'x': 0.4, 'y': 0, 'z': 0},
        presets=[],
        poi_targets={
            'table': {'pan': 41189, 'tilt': 13989},
            'ref_0_0_0': {'pan': 45739, 'tilt': 1654},
            'ref_1_1_0': {'pan': 38358, 'tilt': 18205},
        },
    )
    sm.fixtures = [head]

    sm.song_length_seconds = 4.0
    sm.cue_sheet = CueSheet(
        song_filename='test_song',
        entries=[
            CueEntry(
                time=0.0,
                fixture_id='head_el150',
                effect='sweep',
                duration=3.0,
                data={
                    'subject_POI': 'table',
                    'start_POI': 'ref_0_0_0',
                    'end_POI': 'ref_1_1_0',
                    'duration': 3.0,
                    'easing': 0.5,
                },
            ),
        ],
    )

    canvas = sm._render_cue_sheet_to_canvas()
    frame_start = int(round(0.0 * FPS))
    frame_quarter = int(round(0.75 * FPS))
    frame_mid = int(round(1.5 * FPS))
    frame_three_quarter = int(round(2.25 * FPS))
    frame_end = int(round(3.0 * FPS))

    start_pan = 45739
    start_tilt = 1654
    subject_pan = 41189
    subject_tilt = 13989
    end_pan = 38358
    end_tilt = 18205

    view_start = canvas.frame_view(frame_start)
    pan_start = (int(view_start[1 - 1]) << 8) | int(view_start[2 - 1])
    tilt_start = (int(view_start[3 - 1]) << 8) | int(view_start[4 - 1])
    assert abs(pan_start - start_pan) <= 1
    assert abs(tilt_start - start_tilt) <= 1
    assert int(view_start[6 - 1]) == 0

    view_quarter = canvas.frame_view(frame_quarter)
    pan_quarter = (int(view_quarter[1 - 1]) << 8) | int(view_quarter[2 - 1])
    dim_quarter = int(view_quarter[6 - 1])
    linear_halfway_pan = start_pan + int(round((subject_pan - start_pan) * 0.5))
    assert pan_quarter > linear_halfway_pan
    assert dim_quarter < 127

    view_mid = canvas.frame_view(frame_mid)
    pan_mid = (int(view_mid[1 - 1]) << 8) | int(view_mid[2 - 1])
    tilt_mid = (int(view_mid[3 - 1]) << 8) | int(view_mid[4 - 1])
    assert abs(pan_mid - subject_pan) <= 1
    assert abs(tilt_mid - subject_tilt) <= 1
    assert int(view_mid[6 - 1]) == 255

    view_three_quarter = canvas.frame_view(frame_three_quarter)
    dim_three_quarter = int(view_three_quarter[6 - 1])
    assert dim_three_quarter < 127

    view_end = canvas.frame_view(frame_end)
    pan_end = (int(view_end[1 - 1]) << 8) | int(view_end[2 - 1])
    tilt_end = (int(view_end[3 - 1]) << 8) | int(view_end[4 - 1])
    assert abs(pan_end - end_pan) <= 1
    assert abs(tilt_end - end_tilt) <= 1
    assert int(view_end[6 - 1]) == 0


def test_dmx_canvas_renders_moving_head_sweep_uses_end_poi_when_provided():
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
        poi_targets={
            'start': {'pan': 20000, 'tilt': 12000},
            'subject': {'pan': 30000, 'tilt': 15000},
            'ready': {'pan': 25000, 'tilt': 9000},
        },
    )
    sm.fixtures = [head]

    sm.song_length_seconds = 2.5
    sm.cue_sheet = CueSheet(
        song_filename='test_song',
        entries=[
            CueEntry(
                time=0.0,
                fixture_id='head_1',
                effect='sweep',
                duration=2.0,
                data={
                    'subject_POI': 'subject',
                    'start_POI': 'start',
                    'end_POI': 'ready',
                    'duration': 2.0,
                    'easing': 0.0,
                },
            ),
        ],
    )

    canvas = sm._render_cue_sheet_to_canvas()
    frame_end = int(round(2.0 * FPS))
    view_end = canvas.frame_view(frame_end)

    pan_end = (int(view_end[1 - 1]) << 8) | int(view_end[2 - 1])
    tilt_end = (int(view_end[3 - 1]) << 8) | int(view_end[4 - 1])
    assert abs(pan_end - 25000) <= 1
    assert abs(tilt_end - 9000) <= 1
    assert int(view_end[5 - 1]) == 0


def test_dmx_canvas_renders_simultaneous_mini_beam_sweep_with_end_poi():
    sm = StateManager(Path('.'))
    head_l = MovingHead(
        id='mini_beam_prism_l',
        name='Mini Beam Prism (L)',
        type='moving_head',
        channels={
            'pan_msb': 42,
            'pan_lsb': 43,
            'tilt_msb': 44,
            'tilt_lsb': 45,
            'dim': 47,
            'strobe': 48,
        },
        location={'x': 0.15, 'y': 0.2, 'z': 0.0},
        presets=[],
        poi_targets={
            'ref_0_0_0': {'pan': 47455, 'tilt': 0},
            'table': {'pan': 41376, 'tilt': 13664},
            'ref_1_0_0': {'pan': 46762, 'tilt': 18701},
        },
    )
    head_r = MovingHead(
        id='mini_beam_prism_r',
        name='Mini Beam Prism (R)',
        type='moving_head',
        channels={
            'pan_msb': 54,
            'pan_lsb': 55,
            'tilt_msb': 56,
            'tilt_lsb': 57,
            'dim': 59,
            'strobe': 60,
        },
        location={'x': 0.85, 'y': 0.2, 'z': 0.0},
        presets=[],
        poi_targets={
            'ref_0_0_0': {'pan': 40657, 'tilt': 20425},
            'table': {'pan': 46332, 'tilt': 15402},
            'ref_1_0_0': {'pan': 40718, 'tilt': 4271},
        },
    )
    sm.fixtures = [head_l, head_r]

    sm.song_length_seconds = 4.0
    sm.cue_sheet = CueSheet(
        song_filename='test_song',
        entries=[
            CueEntry(
                time=0.0,
                fixture_id='mini_beam_prism_l',
                effect='sweep',
                duration=3.0,
                data={
                    'start_POI': 'ref_0_0_0',
                    'subject_POI': 'table',
                    'end_POI': 'ref_1_0_0',
                    'duration': 3.0,
                    'easing': 0.5,
                },
            ),
            CueEntry(
                time=0.0,
                fixture_id='mini_beam_prism_r',
                effect='sweep',
                duration=3.0,
                data={
                    'start_POI': 'ref_0_0_0',
                    'subject_POI': 'table',
                    'end_POI': 'ref_1_0_0',
                    'duration': 3.0,
                    'easing': 0.5,
                },
            ),
        ],
    )

    canvas = sm._render_cue_sheet_to_canvas()
    frame_start = int(round(0.0 * FPS))
    frame_end = int(round(3.0 * FPS))

    view_start = canvas.frame_view(frame_start)
    pan_l_start = (int(view_start[42 - 1]) << 8) | int(view_start[43 - 1])
    tilt_l_start = (int(view_start[44 - 1]) << 8) | int(view_start[45 - 1])
    pan_r_start = (int(view_start[54 - 1]) << 8) | int(view_start[55 - 1])
    tilt_r_start = (int(view_start[56 - 1]) << 8) | int(view_start[57 - 1])
    assert abs(pan_l_start - 47455) <= 1
    assert abs(tilt_l_start - 0) <= 1
    assert abs(pan_r_start - 40657) <= 1
    assert abs(tilt_r_start - 20425) <= 1

    view_end = canvas.frame_view(frame_end)
    pan_l_end = (int(view_end[42 - 1]) << 8) | int(view_end[43 - 1])
    tilt_l_end = (int(view_end[44 - 1]) << 8) | int(view_end[45 - 1])
    pan_r_end = (int(view_end[54 - 1]) << 8) | int(view_end[55 - 1])
    tilt_r_end = (int(view_end[56 - 1]) << 8) | int(view_end[57 - 1])
    assert abs(pan_l_end - 46762) <= 1
    assert abs(tilt_l_end - 18701) <= 1
    assert abs(pan_r_end - 40718) <= 1
    assert abs(tilt_r_end - 4271) <= 1
    assert int(view_end[47 - 1]) == 0
    assert int(view_end[59 - 1]) == 0


def test_dmx_canvas_renders_sweep_arc_strength_zero_is_linear():
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
            'dim': 6,
            'shutter': 7,
        },
        location={'x': 0.4, 'y': 0, 'z': 0},
        presets=[],
        poi_targets={
            'table': {'pan': 41189, 'tilt': 13989},
            'ref_0_0_0': {'pan': 45739, 'tilt': 1654},
            'ref_1_1_0': {'pan': 38358, 'tilt': 18205},
        },
    )
    sm.fixtures = [head]

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
                    'start_POI': 'ref_0_0_0',
                    'subject_POI': 'table',
                    'end_POI': 'ref_1_1_0',
                    'duration': 2.0,
                    'easing': 0.0,
                    'arc_strength': 0.0,
                },
            ),
        ],
    )

    canvas = sm._render_cue_sheet_to_canvas()
    frame_first_leg_mid = int(round(0.5 * FPS))
    view_mid = canvas.frame_view(frame_first_leg_mid)

    pan_mid = (int(view_mid[1 - 1]) << 8) | int(view_mid[2 - 1])
    tilt_mid = (int(view_mid[3 - 1]) << 8) | int(view_mid[4 - 1])

    expected_pan = int(round((45739 + 41189) / 2.0))
    expected_tilt = int(round((1654 + 13989) / 2.0))
    assert abs(pan_mid - expected_pan) <= 1
    assert abs(tilt_mid - expected_tilt) <= 1


def test_dmx_canvas_renders_sweep_arc_strength_positive_adds_arc():
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
            'dim': 6,
            'shutter': 7,
        },
        location={'x': 0.4, 'y': 0, 'z': 0},
        presets=[],
        poi_targets={
            'table': {'pan': 41189, 'tilt': 13989},
            'ref_0_0_0': {'pan': 45739, 'tilt': 1654},
            'ref_1_1_0': {'pan': 38358, 'tilt': 18205},
        },
    )
    sm.fixtures = [head]

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
                    'start_POI': 'ref_0_0_0',
                    'subject_POI': 'table',
                    'end_POI': 'ref_1_1_0',
                    'duration': 2.0,
                    'easing': 0.0,
                    'arc_strength': 0.03,
                },
            ),
        ],
    )

    canvas = sm._render_cue_sheet_to_canvas()
    frame_first_leg_mid = int(round(0.5 * FPS))
    view_mid = canvas.frame_view(frame_first_leg_mid)

    pan_mid = (int(view_mid[1 - 1]) << 8) | int(view_mid[2 - 1])
    tilt_mid = (int(view_mid[3 - 1]) << 8) | int(view_mid[4 - 1])

    linear_pan = int(round((45739 + 41189) / 2.0))
    linear_tilt = int(round((1654 + 13989) / 2.0))
    assert abs(pan_mid - linear_pan) >= 50
    assert abs(tilt_mid - linear_tilt) >= 20


def test_dmx_canvas_renders_sweep_dimmer_stays_off_until_close_to_subject():
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
            'dim': 6,
            'shutter': 7,
        },
        location={'x': 0.4, 'y': 0, 'z': 0},
        presets=[],
        poi_targets={
            'table': {'pan': 41189, 'tilt': 13989},
            'ref_0_0_0': {'pan': 45739, 'tilt': 1654},
            'ref_1_1_0': {'pan': 38358, 'tilt': 18205},
        },
    )
    sm.fixtures = [head]

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
                    'start_POI': 'ref_0_0_0',
                    'subject_POI': 'table',
                    'end_POI': 'ref_1_1_0',
                    'duration': 2.0,
                    'easing': 0.0,
                    'arc_strength': 0.0,
                    'subject_close_ratio': 0.2,
                    'max_dim': 200,
                },
            ),
        ],
    )

    canvas = sm._render_cue_sheet_to_canvas()
    frame_far = int(round(0.5 * FPS))
    frame_close = int(round(0.90 * FPS))
    frame_very_close = int(round(0.98 * FPS))

    view_far = canvas.frame_view(frame_far)
    view_close = canvas.frame_view(frame_close)
    view_very_close = canvas.frame_view(frame_very_close)

    assert int(view_far[6 - 1]) == 0
    assert int(view_close[6 - 1]) > 0
    assert int(view_very_close[6 - 1]) > int(view_close[6 - 1])


def test_dmx_canvas_renders_sweep_dimmer_fades_out_quickly_after_subject_when_very_close_ratio():
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
            'dim': 6,
            'shutter': 7,
        },
        location={'x': 0.4, 'y': 0, 'z': 0},
        presets=[],
        poi_targets={
            'table': {'pan': 41189, 'tilt': 13989},
            'ref_0_0_0': {'pan': 45739, 'tilt': 1654},
            'ref_1_1_0': {'pan': 38358, 'tilt': 18205},
        },
    )
    sm.fixtures = [head]

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
                    'start_POI': 'ref_0_0_0',
                    'subject_POI': 'table',
                    'end_POI': 'ref_1_1_0',
                    'duration': 2.0,
                    'easing': 0.0,
                    'arc_strength': 0.0,
                    'subject_close_ratio': 0.01,
                    'max_dim': 200,
                },
            ),
        ],
    )

    canvas = sm._render_cue_sheet_to_canvas()
    frame_at_subject = int(round(1.0 * FPS))
    frame_after_depart = int(round(1.1 * FPS))

    view_at_subject = canvas.frame_view(frame_at_subject)
    view_after_depart = canvas.frame_view(frame_after_depart)

    assert int(view_at_subject[6 - 1]) > 0
    assert int(view_after_depart[6 - 1]) == 0
