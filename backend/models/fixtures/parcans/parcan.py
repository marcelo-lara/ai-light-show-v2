from typing import Dict, Any, List
from models.fixtures.fixture import Fixture
from .set_channels import handle as handle_set_channels
from .flash import handle as handle_flash
from .strobe import handle as handle_strobe
from .fade_in import handle as handle_fade_in
from .full import handle as handle_full


class Parcan(Fixture):
    type: str = "parcan"

    # Keep older `actions` field for fixtures.json compatibility but prefer `effects`.
    actions: List[str] = []

    def to_dmx(self) -> Dict[int, int]:
        dmx: Dict[int, int] = {}
        for name, ch in self.channels.items():
            val = int(self.current_values.get(name, 0) or 0)
            dmx[ch] = max(0, min(255, val))
        return dmx

    def apply_preset(self, preset: Dict[str, Any]) -> None:
        for k, v in preset.items():
            if k in self.channels:
                self.set_channel_value(k, v)

    def render_effect(
        self,
        universe: bytearray,
        *,
        effect: str,
        frame_index: int,
        start_frame: int,
        end_frame: int,
        fps: int,
        data: Dict[str, Any],
        render_state: Dict[str, Any],
    ) -> None:
        effect = (effect or "").lower().strip()
        effect_handlers = {
            "set_channels": handle_set_channels,
            "flash": handle_flash,
            "strobe": handle_strobe,
            "fade_in": handle_fade_in,
            "full": handle_full,
        }
        handler = effect_handlers.get(effect)
        if handler:
            handler(self, universe, frame_index, start_frame, end_frame, fps, data, render_state)