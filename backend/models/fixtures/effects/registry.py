import abc
from typing import Any, Dict, List, Sequence, Set

EFFECT_TAG_VOCABULARY: Set[str] = {
    "accent",
    "drop",
    "focus",
    "hard",
    "long",
    "movement",
    "release",
    "rise",
    "short",
    "soft",
    "spike",
    "static",
    "sustain",
    "tension",
    "valley",
    "wash",
}


def _normalize_tags(tags: Sequence[str]) -> List[str]:
    normalized: List[str] = []
    seen: Set[str] = set()
    for raw_tag in tags:
        tag = str(raw_tag or "").strip().lower()
        if not tag or tag in seen:
            continue
        if tag not in EFFECT_TAG_VOCABULARY:
            raise ValueError(f"unsupported_effect_tag:{tag}")
        seen.add(tag)
        normalized.append(tag)
    return normalized

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
    def tags(self) -> List[str]:
        """Controlled effect tags used for assistant reasoning and discovery."""
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
        _normalize_tags(effect_instance.tags)
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

    @classmethod
    def serialize(cls, effect: Effect) -> Dict[str, Any]:
        return {
            "id": effect.id,
            "name": effect.name,
            "description": effect.description,
            "tags": _normalize_tags(effect.tags),
            "schema": effect.schema,
        }

    @classmethod
    def serialize_all(cls) -> Dict[str, Dict[str, Any]]:
        return {effect.id: cls.serialize(effect) for effect in cls.get_all()}

    @classmethod
    def get_supported_effect_metadata(cls, fixture: Any) -> List[Dict[str, Any]]:
        supported = [cls.serialize(effect) for effect in cls.get_all() if effect.supports(fixture)]
        return sorted(supported, key=lambda item: str(item["id"]))

# Singleton accessor
REGISTRY = EffectRegistry()
