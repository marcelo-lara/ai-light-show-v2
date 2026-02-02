import math
from pathlib import Path

from backend.store.state import StateManager, FPS
from backend.models.cue import CueSheet, CueEntry
from backend.models.fixtures.parcans.parcan import Parcan


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
            CueEntry(time=0.0, fixture_id='parcan_l', action='set_channels', data={'channels': {'blue': 255}}),
            CueEntry(time=0.5, fixture_id='parcan_r', action='set_channels', data={'channels': {'blue': 255}}),
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
