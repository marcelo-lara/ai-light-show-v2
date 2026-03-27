import abc
from typing import Any, Dict, List, Set, Type

class Effect(abc.ABC):
    """Base class for all capability-based fixture effects."""

    @property
    @abc.abstractmethod
    def id(self) -> str:
        """The unique string ID of the effect (e.g. 'blackout')."""
        pass

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """A friendly name for the effect."""
        pass

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """A detailed description of what the effect does, for LLM context."""
        pass

    @property
    @abc.abstractmethod
    def schema(self) -> Dict[str, Any]:
        """A JSON schema describing the `data` payload expected by the effect."""
        pass

    @abc.abstractmethod
    def supports(self, fixture: Any) -> bool:
        """Return True if this effect supports being executed on the given fixture."""
        pass

    @abc.abstractmethod
    def render(
        self,
        fixture: Any,
        universe: bytearray,
        *,
        frame_index: int,
        start_frame: int,
        end_frame: int,
        fps: int,
        data: Dict[str, Any],
        render_state: Dict[str, Any],
    ) -> None:
        """Render the effect into the universe for the given frame index."""
        pass

class EffectRegistry:
    _effects: Dict[str, Effect] = {}

    @classmethod
    def register(cls, effect_instance: Effect) -> None:
        cls._effects[effect_instance.id] = effect_instance

    @classmethod
    def get(cls, effect_id: str) -> Effect | None:
        return cls._effects.get(effect_id)

    @classmethod
    def get_all(cls) -> List[Effect]:
        return list(cls._effects.values())

    @classmethod
    def get_supported_effects(cls, fixture: Any) -> Set[str]:
        return {e.id for e in cls._effects.values() if e.supports(fixture)}

# Singleton accessor
REGISTRY = EffectRegistry()
