from .registry import Effect, EffectRegistry, REGISTRY

from .blackout import BlackoutEffect
from .full import FullEffect
from .set_channels import SetChannelsEffect
from .flash import FlashEffect
from .strobe import StrobeEffect
from .fade_in import FadeInEffect
from .fade_out import FadeOutEffect
from .color_fade import ColorFadeEffect
from .moving_head import MoveToEffect, MoveToPoiEffect, OrbitEffect, SweepEffect

__all__ = [
    "Effect",
    "EffectRegistry",
    "REGISTRY",
]
