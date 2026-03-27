from typing import Any, Dict
from ..effects.registry import Effect, REGISTRY

class MoveToEffect(Effect):
    @property
    def id(self) -> str: return "move_to"
    @property
    def name(self) -> str: return "Move To"
    @property
    def description(self) -> str: return "Moves the fixture to specific pan/tilt values."
    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"pan": {"type": "number"}, "tilt": {"type": "number"}},
            "additionalProperties": True,
        }
    def supports(self, fixture: Any) -> bool:
        meta = getattr(fixture, "meta_channels", {})
        return "pan" in meta or "tilt" in meta

    def render(self, fixture: Any, universe: bytearray, *, frame_index: int, start_frame: int, end_frame: int, fps: int, data: Dict[str, Any], render_state: Dict[str, Any]) -> None:
        from ..moving_heads.move_to import handle
        handle(fixture, universe, frame_index, start_frame, end_frame, fps, data, render_state)

class MoveToPoiEffect(Effect):
    @property
    def id(self) -> str: return "move_to_poi"
    @property
    def name(self) -> str: return "Move To POI"
    @property
    def description(self) -> str: return "Moves the fixture to target POI."
    @property
    def schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {"poi_id": {"type": "string"}}}
    def supports(self, fixture: Any) -> bool:
        meta = getattr(fixture, "meta_channels", {})
        return "pan" in meta or "tilt" in meta
    def render(self, fixture: Any, universe: bytearray, *, frame_index: int, start_frame: int, end_frame: int, fps: int, data: Dict[str, Any], render_state: Dict[str, Any]) -> None:
        from ..moving_heads.move_to_poi import handle
        handle(fixture, universe, frame_index, start_frame, end_frame, fps, data, render_state)

class SeekEffect(Effect):
    @property
    def id(self) -> str: return "seek"
    @property
    def name(self) -> str: return "Seek"
    @property
    def description(self) -> str: return "Smoothly seeks to a target POI or pan/tilt over time."
    @property
    def schema(self) -> Dict[str, Any]: return {"type": "object", "additionalProperties": True}
    def supports(self, fixture: Any) -> bool:
        meta = getattr(fixture, "meta_channels", {})
        return "pan" in meta or "tilt" in meta
    def render(self, fixture: Any, universe: bytearray, *, frame_index: int, start_frame: int, end_frame: int, fps: int, data: Dict[str, Any], render_state: Dict[str, Any]) -> None:
        from ..moving_heads.seek import handle
        handle(fixture, universe, frame_index, start_frame, end_frame, fps, data, render_state)

class SweepEffect(Effect):
    @property
    def id(self) -> str: return "sweep"
    @property
    def name(self) -> str: return "Sweep"
    @property
    def description(self) -> str: return "Sweeps the fixture from a start POI through a subject POI back and forth."
    @property
    def schema(self) -> Dict[str, Any]: return {"type": "object", "additionalProperties": True}
    def supports(self, fixture: Any) -> bool:
        meta = getattr(fixture, "meta_channels", {})
        return "pan" in meta or "tilt" in meta
    def render(self, fixture: Any, universe: bytearray, *, frame_index: int, start_frame: int, end_frame: int, fps: int, data: Dict[str, Any], render_state: Dict[str, Any]) -> None:
        from ..moving_heads.sweep import handle
        handle(fixture, universe, frame_index, start_frame, end_frame, fps, data, render_state)

REGISTRY.register(MoveToEffect())
REGISTRY.register(MoveToPoiEffect())
REGISTRY.register(SeekEffect())
REGISTRY.register(SweepEffect())
