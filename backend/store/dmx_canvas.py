from __future__ import annotations

from dataclasses import dataclass
from typing import Final


DMX_CHANNELS: Final[int] = 512


@dataclass
class DMXCanvas:
    """Flat DMX frame buffer.

    Frames are stored sequentially in a single bytearray:
      buffer[frame_index * 512 : (frame_index + 1) * 512]

    This keeps memory overhead low compared to a Python list of per-frame objects.
    """

    fps: int
    total_frames: int
    buffer: bytearray

    @staticmethod
    def allocate(*, fps: int, total_frames: int) -> "DMXCanvas":
        if fps <= 0:
            raise ValueError("fps must be > 0")
        if total_frames <= 0:
            raise ValueError("total_frames must be > 0")
        return DMXCanvas(fps=fps, total_frames=total_frames, buffer=bytearray(total_frames * DMX_CHANNELS))

    def clamp_frame_index(self, frame_index: int) -> int:
        if frame_index < 0:
            return 0
        if frame_index >= self.total_frames:
            return self.total_frames - 1
        return frame_index

    def frame_view(self, frame_index: int) -> memoryview:
        idx = self.clamp_frame_index(frame_index)
        start = idx * DMX_CHANNELS
        end = start + DMX_CHANNELS
        return memoryview(self.buffer)[start:end]

    def set_frame(self, frame_index: int, universe: bytearray) -> None:
        if len(universe) != DMX_CHANNELS:
            raise ValueError(f"universe must be {DMX_CHANNELS} bytes")
        idx = self.clamp_frame_index(frame_index)
        start = idx * DMX_CHANNELS
        self.buffer[start : start + DMX_CHANNELS] = universe
