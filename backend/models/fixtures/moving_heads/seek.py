from typing import Any, Dict

from .seek_helpers import spiral_seek_position
from .sweep_helpers import find_intensity_channel_key
from .travel_helpers import EFFECT_SETTLE_SECONDS, limit_axis_step, max_axis_step_per_frame


def handle(self, universe: bytearray, frame_index: int, start_frame: int, end_frame: int, fps: int, data: Dict[str, Any], render_state: Dict[str, Any]) -> None:
    # Seek: orbit around subject_POI, then spiral into it.
    if not (self._has_axis_16bit("pan") and self._has_axis_16bit("tilt")):
        return

    payload = data or {}
    subject_poi = str(payload.get("subject_POI") or "").strip()
    start_poi = str(payload.get("start_POI") or "").strip()
    if not subject_poi or not start_poi:
        return

    subject_pan_u16, subject_tilt_u16 = self._resolve_poi_pan_tilt_u16(subject_poi)
    start_pan_u16, start_tilt_u16 = self._resolve_poi_pan_tilt_u16(start_poi)
    if subject_pan_u16 is None or subject_tilt_u16 is None or start_pan_u16 is None or start_tilt_u16 is None:
        return

    preroll_frames = max(0, int(payload.get("__seek_preroll_frames") or 0))
    settle_frames = min(max(0, int(round(EFFECT_SETTLE_SECONDS * max(1, fps)))), preroll_frames)
    move_frames = max(0, preroll_frames - settle_frames)
    visible_start_frame = start_frame + preroll_frames

    if "seek_initial_pan_u16" not in render_state or "seek_initial_tilt_u16" not in render_state:
        render_state["seek_initial_pan_u16"] = int(self._read_axis_u16_from_universe(universe, "pan") or 0)
        render_state["seek_initial_tilt_u16"] = int(self._read_axis_u16_from_universe(universe, "tilt") or 0)

    if "seek_last_pan_u16" not in render_state or "seek_last_tilt_u16" not in render_state:
        render_state["seek_last_pan_u16"] = int(render_state.get("seek_initial_pan_u16", 0))
        render_state["seek_last_tilt_u16"] = int(render_state.get("seek_initial_tilt_u16", 0))

    intensity_key = find_intensity_channel_key(self)
    if intensity_key and "seek_initial_intensity" not in render_state:
        render_state["seek_initial_intensity"] = int(universe[self.absolute_channels[intensity_key] - 1])

    last_pan_u16 = int(render_state.get("seek_last_pan_u16", 0))
    last_tilt_u16 = int(render_state.get("seek_last_tilt_u16", 0))
    max_pan_step, max_tilt_step = max_axis_step_per_frame(self, fps)

    if frame_index < start_frame + move_frames:
        move_progress = (frame_index - start_frame) / float(max(1, move_frames))
        target_pan_u16 = int(round(int(render_state.get("seek_initial_pan_u16", 0)) + ((int(start_pan_u16) - int(render_state.get("seek_initial_pan_u16", 0))) * move_progress)))
        target_tilt_u16 = int(round(int(render_state.get("seek_initial_tilt_u16", 0)) + ((int(start_tilt_u16) - int(render_state.get("seek_initial_tilt_u16", 0))) * move_progress)))
        pan_value = self._clamp_u16(limit_axis_step(last_pan_u16, target_pan_u16, max_pan_step))
        tilt_value = self._clamp_u16(limit_axis_step(last_tilt_u16, target_tilt_u16, max_tilt_step))
        if intensity_key:
            self._write_channel(universe, intensity_key, 0)
    elif frame_index < visible_start_frame:
        pan_value = self._clamp_u16(start_pan_u16)
        tilt_value = self._clamp_u16(start_tilt_u16)
        if intensity_key:
            self._write_channel(universe, intensity_key, 0)
    elif end_frame <= visible_start_frame:
        progress = 1.0
        target_pan_u16, target_tilt_u16 = int(subject_pan_u16), int(subject_tilt_u16)
        pan_value = self._clamp_u16(limit_axis_step(last_pan_u16, target_pan_u16, max_pan_step))
        tilt_value = self._clamp_u16(limit_axis_step(last_tilt_u16, target_tilt_u16, max_tilt_step))
        if intensity_key:
            self._write_channel(universe, intensity_key, int(render_state.get("seek_initial_intensity", 0)))
    else:
        duration_frames = max(1, end_frame - visible_start_frame)
        progress = max(0.0, min(1.0, (frame_index - visible_start_frame) / float(duration_frames)))
        target_pan_u16, target_tilt_u16 = spiral_seek_position(
            start_pan=int(start_pan_u16),
            start_tilt=int(start_tilt_u16),
            subject_pan=int(subject_pan_u16),
            subject_tilt=int(subject_tilt_u16),
            progress=progress,
            orbits=payload.get("orbits", 1.0),
            easing=payload.get("easing", "late_focus"),
        )
        pan_value = self._clamp_u16(limit_axis_step(last_pan_u16, target_pan_u16, max_pan_step))
        tilt_value = self._clamp_u16(limit_axis_step(last_tilt_u16, target_tilt_u16, max_tilt_step))
        if intensity_key:
            self._write_channel(universe, intensity_key, int(render_state.get("seek_initial_intensity", 0)))

    self._write_axis_u16_to_universe(universe, "pan", pan_value)
    self._write_axis_u16_to_universe(universe, "tilt", tilt_value)
    render_state["seek_last_pan_u16"] = int(pan_value)
    render_state["seek_last_tilt_u16"] = int(tilt_value)