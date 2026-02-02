from typing import Any, Dict
from models.fixtures.fixture import Fixture
from .set_channels import handle as handle_set_channels
from .move_to import handle as handle_move_to
from .seek import handle as handle_seek
from .strobe import handle as handle_strobe
from .full import handle as handle_full
from .flash import handle as handle_flash


class MovingHead(Fixture):
    type: str = "moving_head"

    def to_dmx(self) -> Dict[int, int]:
        dmx: Dict[int, int] = {}
        for name, ch in self.channels.items():
            raw = self.current_values.get(name, 0) or 0
            if name in ("pan", "tilt"):
                max_deg = int(self.meta.get(f"{name}_range", 540))
                val = int(max(0, min(max_deg, float(raw))) * 255 / (max_deg if max_deg else 1))
            else:
                val = int(raw)
            dmx[ch] = max(0, min(255, val))
        return dmx

    def apply_preset(self, preset: Dict[str, Any]) -> None:
        for k, v in preset.items():
            if k in self.channels:
                if k in ("pan", "tilt"):
                    self.current_values[k] = float(v)
                else:
                    self.set_channel_value(k, v)

    def _deg_to_byte(self, axis: str, degrees: Any) -> int:
        try:
            deg = float(degrees)
        except Exception:
            return 0
        max_deg = int(self.meta.get(f"{axis}_range", 540))
        if max_deg <= 0:
            max_deg = 540
        deg = max(0.0, min(float(max_deg), deg))
        return int(round(deg * 255.0 / float(max_deg)))

    def render_action(
        self,
        universe: bytearray,
        *,
        action: str,
        frame_index: int,
        start_frame: int,
        end_frame: int,
        fps: int,
        data: Dict[str, Any],
        render_state: Dict[str, Any],
    ) -> None:
        action = (action or "").lower().strip()
        action_handlers = {
            "set_channels": handle_set_channels,
            "move_to": handle_move_to,
            "seek": handle_seek,
            "strobe": handle_strobe,
            "full": handle_full,
            "flash": handle_flash,
        }
        handler = action_handlers.get(action)
        if handler:
            handler(self, universe, frame_index, start_frame, end_frame, fps, data, render_state)



    def move_to(self, pan: float, tilt: float) -> None:
        pass

    def arm_fixture(self) -> None:
        # Send arm values
        for channel_name, value in self.arm.items():
            if channel_name in self.channels:
                channel_num = self.channels[channel_name]
                self.current_values[channel_name] = value
