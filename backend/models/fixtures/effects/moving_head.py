from typing import Any, Dict
from ..effects.registry import Effect, REGISTRY


def _supports_pan_tilt(fixture: Any) -> bool:
    meta = getattr(fixture, "meta_channels", {})
    return "pan" in meta or "tilt" in meta

class MoveToEffect(Effect):
    @property
    def id(self) -> str: return "move_to"
    @property
    def name(self) -> str: return "Move To"
    @property
    def description(self) -> str: return "Moves the head to a specific position when you need a direct reposition or focus change."
    @property
    def tags(self) -> list[str]: return ["movement", "focus", "short"]
    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"pan": {"type": "number"}, "tilt": {"type": "number"}},
            "additionalProperties": True,
        }
    def supports(self, fixture: Any) -> bool:
        return _supports_pan_tilt(fixture)

    def render(self, fixture: Any, universe: bytearray, *, frame_index: int, start_frame: int, end_frame: int, fps: int, data: Dict[str, Any], render_state: Dict[str, Any]) -> None:
        from ..moving_heads.move_to import handle
        handle(fixture, universe, frame_index, start_frame, end_frame, fps, data, render_state)

class MoveToPoiEffect(Effect):
    @property
    def id(self) -> str: return "move_to_poi"
    @property
    def name(self) -> str: return "Move To POI"
    @property
    def description(self) -> str: return "Moves the head to a named POI for direct subject focus or quick staging changes."
    @property
    def tags(self) -> list[str]: return ["movement", "focus", "short", "static"]
    @property
    def schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {"poi_id": {"type": "string"}}}
    def supports(self, fixture: Any) -> bool:
        return _supports_pan_tilt(fixture)
    def render(self, fixture: Any, universe: bytearray, *, frame_index: int, start_frame: int, end_frame: int, fps: int, data: Dict[str, Any], render_state: Dict[str, Any]) -> None:
        from ..moving_heads.move_to_poi import handle
        handle(fixture, universe, frame_index, start_frame, end_frame, fps, data, render_state)

class CircleEffect(Effect):
    @property
    def id(self) -> str: return "circle"
    @property
    def name(self) -> str: return "Circle"
    @property
    def description(self) -> str: return "Moves around a POI using geometric reference points, which suits sustained spatial motion without hardcoded pan-tilt arcs."
    @property
    def tags(self) -> list[str]: return ["movement", "focus", "long", "soft"]
    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "target_poi": {"type": "string"},
                "radius": {"type": "number"},
                "orbits": {"type": "number"},
            },
            "required": ["target_poi", "radius"],
            "additionalProperties": True,
        }
    def supports(self, fixture: Any) -> bool:
        return _supports_pan_tilt(fixture)
    def render(self, fixture: Any, universe: bytearray, *, frame_index: int, start_frame: int, end_frame: int, fps: int, data: Dict[str, Any], render_state: Dict[str, Any]) -> None:
        from ..moving_heads.circle import handle
        handle(fixture, universe, frame_index, start_frame, end_frame, fps, data, render_state)

class OrbitEffect(Effect):
    @property
    def id(self) -> str: return "orbit"
    @property
    def name(self) -> str: return "Orbit"
    @property
    def description(self) -> str: return "Glides toward a target over time, which suits builds, tightening focus, and rising tension."
    @property
    def tags(self) -> list[str]: return ["rise", "movement", "focus", "tension", "long"]
    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "subject_POI": {"type": "string"},
                "start_POI": {"type": "string"},
                "orbits": {"type": "number"},
                "easing": {"type": "string"},
                "write_dimmer": {"type": "boolean"},
            },
            "additionalProperties": True,
        }
    def supports(self, fixture: Any) -> bool:
        return _supports_pan_tilt(fixture)
    def render(self, fixture: Any, universe: bytearray, *, frame_index: int, start_frame: int, end_frame: int, fps: int, data: Dict[str, Any], render_state: Dict[str, Any]) -> None:
        from ..moving_heads.orbit import handle
        handle(fixture, universe, frame_index, start_frame, end_frame, fps, data, render_state)

class OrbitOutEffect(Effect):
    @property
    def id(self) -> str: return "orbit_out"
    @property
    def name(self) -> str: return "Orbit Out"
    @property
    def description(self) -> str: return "Starts on the subject and spirals outward toward a start POI, which suits releases, exits, and expanding focus."
    @property
    def tags(self) -> list[str]: return ["release", "movement", "focus", "tension", "long"]
    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "subject_POI": {"type": "string"},
                "start_POI": {"type": "string"},
                "orbits": {"type": "number"},
                "easing": {"type": "string"},
                "write_dimmer": {"type": "boolean"},
            },
            "additionalProperties": True,
        }
    def supports(self, fixture: Any) -> bool:
        return _supports_pan_tilt(fixture)
    def render(self, fixture: Any, universe: bytearray, *, frame_index: int, start_frame: int, end_frame: int, fps: int, data: Dict[str, Any], render_state: Dict[str, Any]) -> None:
        from ..moving_heads.orbit_out import handle
        handle(fixture, universe, frame_index, start_frame, end_frame, fps, data, render_state)

class SweepEffect(Effect):
    @property
    def id(self) -> str: return "sweep"
    @property
    def name(self) -> str: return "Sweep"
    @property
    def description(self) -> str: return "Moves across space in a broad arc, which suits longer phrases, soft motion, and sustained tension."
    @property
    def tags(self) -> list[str]: return ["movement", "tension", "long", "soft"]
    @property
    def schema(self) -> Dict[str, Any]: return {"type": "object", "additionalProperties": True}
    def supports(self, fixture: Any) -> bool:
        return _supports_pan_tilt(fixture)
    def render(self, fixture: Any, universe: bytearray, *, frame_index: int, start_frame: int, end_frame: int, fps: int, data: Dict[str, Any], render_state: Dict[str, Any]) -> None:
        from ..moving_heads.sweep import handle
        handle(fixture, universe, frame_index, start_frame, end_frame, fps, data, render_state)

REGISTRY.register(MoveToEffect())
REGISTRY.register(MoveToPoiEffect())
REGISTRY.register(CircleEffect())
REGISTRY.register(OrbitEffect())
REGISTRY.register(OrbitOutEffect())
REGISTRY.register(SweepEffect())
