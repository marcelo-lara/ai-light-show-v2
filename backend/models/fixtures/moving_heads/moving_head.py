from typing import Any, Dict, Optional, Tuple
from models.fixtures.fixture import Fixture
from .set_channels import handle as handle_set_channels
from .move_to import handle as handle_move_to
from .seek import handle as handle_seek
from .strobe import handle as handle_strobe
from .full import handle as handle_full
from .flash import handle as handle_flash
from .sweep import handle as handle_sweep


class MovingHead(Fixture):
    type: str = "moving_head"

    def _clamp_u16(self, value: Any) -> int:
        try:
            iv = int(value)
        except Exception:
            return 0
        return max(0, min(65535, iv))

    def _split_u16(self, value_u16: Any) -> Tuple[int, int]:
        v = self._clamp_u16(value_u16)
        return ((v >> 8) & 0xFF, v & 0xFF)

    def _combine_u16(self, msb: Any, lsb: Any) -> int:
        return self._clamp_u16((self._clamp_byte(msb) << 8) | self._clamp_byte(lsb))

    def _has_axis_16bit(self, axis: str) -> bool:
        return f"{axis}_msb" in self.channels and f"{axis}_lsb" in self.channels

    def _read_axis_u16_from_universe(self, universe: bytearray, axis: str) -> Optional[int]:
        if not self._has_axis_16bit(axis):
            return None
        msb_ch = self.channels[f"{axis}_msb"]
        lsb_ch = self.channels[f"{axis}_lsb"]
        msb = int(universe[msb_ch - 1])
        lsb = int(universe[lsb_ch - 1])
        return (msb << 8) | lsb

    def _write_axis_u16_to_universe(self, universe: bytearray, axis: str, value_u16: Any) -> None:
        if not self._has_axis_16bit(axis):
            return
        msb, lsb = self._split_u16(value_u16)
        self._write_channel(universe, self.channels[f"{axis}_msb"], msb)
        self._write_channel(universe, self.channels[f"{axis}_lsb"], lsb)

    def _find_preset_values(self, preset_name: Any) -> Optional[Dict[str, Any]]:
        if not preset_name:
            return None
        needle = str(preset_name).strip().lower()
        for p in self.presets or []:
            try:
                if str(p.get("name", "")).strip().lower() == needle:
                    values = p.get("values")
                    return values if isinstance(values, dict) else None
            except Exception:
                continue
        return None

    def _parse_axis_target_u16(self, axis: str, payload: Dict[str, Any]) -> Optional[int]:
        if not isinstance(payload, dict):
            return None

        # Direct MSB/LSB.
        msb_key = f"{axis}_msb"
        lsb_key = f"{axis}_lsb"
        if msb_key in payload or lsb_key in payload:
            msb = payload.get(msb_key, 0)
            lsb = payload.get(lsb_key, 0)
            return self._combine_u16(msb, lsb)

        # Packed u16 in `pan`/`tilt`.
        if axis in payload:
            raw = payload.get(axis, 0)
            try:
                iv = int(raw)
            except Exception:
                return None

            # If a fine component exists, treat axis as MSB byte.
            fine_key = f"{axis}_fine"
            if fine_key in payload:
                return self._combine_u16(iv, payload.get(fine_key, 0))

            # Otherwise interpret as u16 (0..65535).
            return self._clamp_u16(iv)

        return None

    def _parse_pan_tilt_targets_u16(self, data: Dict[str, Any]) -> Tuple[Optional[int], Optional[int]]:
        payload: Dict[str, Any] = data or {}

        preset_name = payload.get("preset")
        if preset_name:
            preset_values = self._find_preset_values(preset_name) or {}
            pan = self._parse_axis_target_u16("pan", preset_values)
            tilt = self._parse_axis_target_u16("tilt", preset_values)
            return pan, tilt

        return (
            self._parse_axis_target_u16("pan", payload),
            self._parse_axis_target_u16("tilt", payload),
        )

    def to_dmx(self) -> Dict[int, int]:
        dmx: Dict[int, int] = {}

        # 16-bit pan/tilt are stored as u16 in current_values['pan'/'tilt'].
        pan_u16 = self._clamp_u16((self.current_values or {}).get("pan", 0))
        tilt_u16 = self._clamp_u16((self.current_values or {}).get("tilt", 0))
        if "pan_msb" in self.channels:
            dmx[self.channels["pan_msb"]] = (pan_u16 >> 8) & 0xFF
        if "pan_lsb" in self.channels:
            dmx[self.channels["pan_lsb"]] = pan_u16 & 0xFF
        if "tilt_msb" in self.channels:
            dmx[self.channels["tilt_msb"]] = (tilt_u16 >> 8) & 0xFF
        if "tilt_lsb" in self.channels:
            dmx[self.channels["tilt_lsb"]] = tilt_u16 & 0xFF

        for name, ch in (self.channels or {}).items():
            if name in ("pan_msb", "pan_lsb", "tilt_msb", "tilt_lsb"):
                continue
            raw = (self.current_values or {}).get(name, 0) or 0
            dmx[ch] = self._clamp_byte(raw)

        return dmx

    def apply_preset(self, preset: Dict[str, Any]) -> None:
        if not isinstance(preset, dict):
            return

        # Pan/Tilt may be expressed as u16, MSB/LSB pairs, or MSB+fine.
        pan = self._parse_axis_target_u16("pan", preset)
        tilt = self._parse_axis_target_u16("tilt", preset)
        if pan is not None:
            self.current_values["pan"] = self._clamp_u16(pan)
        if tilt is not None:
            self.current_values["tilt"] = self._clamp_u16(tilt)

        # Apply any other direct channels.
        for k, v in preset.items():
            if k in ("pan", "pan_fine", "pan_msb", "pan_lsb", "tilt", "tilt_fine", "tilt_msb", "tilt_lsb"):
                continue
            if k in self.channels:
                self.set_channel_value(k, v)

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
            "sweep": handle_sweep,
        }
        handler = action_handlers.get(action)
        if handler:
            handler(self, universe, frame_index, start_frame, end_frame, fps, data, render_state)
