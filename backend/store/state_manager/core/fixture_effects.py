# pyright: reportAttributeAccessIssue=false

from typing import Optional

from models.fixture import Fixture
from store.dmx_canvas import DMX_CHANNELS


class StateCoreFixtureEffectsMixin:
    def _get_fixture(self, fixture_id: str) -> Optional[Fixture]:
        return next((fixture for fixture in self.fixtures if fixture.id == fixture_id), None)

    def _fixture_supported_effects(self, fixture: Fixture) -> set[str]:
        runtime_effects = {
            "moving_head": {
                "set_channels",
                "move_to",
                "move_to_poi",
                "seek",
                "strobe",
                "full",
                "flash",
                "sweep",
            },
            "parcan": {"set_channels", "flash", "strobe", "fade_in", "full"},
            "rgb": {"set_channels", "flash", "strobe", "fade_in", "full"},
        }.get((fixture.type or "").lower(), {"set_channels"})

        declared = {
            str(effect).strip().lower() for effect in (fixture.effects or []) if str(effect).strip()
        }
        if not declared:
            return runtime_effects
        return runtime_effects.intersection(declared)

    def _set_channel(self, universe: bytearray, channel_1_based: int, value: int) -> None:
        if 1 <= channel_1_based <= DMX_CHANNELS:
            universe[channel_1_based - 1] = max(0, min(255, int(value)))

    def _apply_arm(self, universe: bytearray) -> None:
        for fixture in self.fixtures:
            for _mc_id, mc in fixture.meta_channels.items():
                if mc.arm is None:
                    continue
                if mc.kind == "u16" and mc.channels:
                    msb = (mc.arm >> 8) & 0xFF
                    lsb = mc.arm & 0xFF
                    self._set_channel(universe, fixture.absolute_channels[mc.channels[0]], msb)
                    self._set_channel(universe, fixture.absolute_channels[mc.channels[1]], lsb)
                elif mc.channel:
                    self._set_channel(universe, fixture.absolute_channels[mc.channel], mc.arm)
