from typing import Any, Dict

from .orbit_motion import render_orbit_motion


def handle(self, universe: bytearray, frame_index: int, start_frame: int, end_frame: int, fps: int, data: Dict[str, Any], render_state: Dict[str, Any]) -> None:
    render_orbit_motion(
        self,
        universe,
        frame_index,
        start_frame,
        end_frame,
        fps,
        data,
        render_state,
        outward=True,
        state_prefix="orbit_out",
    )
