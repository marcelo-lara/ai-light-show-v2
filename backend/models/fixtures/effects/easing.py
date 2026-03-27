from typing import Callable

def linear(t: float) -> float:
    return t

def ease_in(t: float) -> float:
    return t * t * t

def ease_out(t: float) -> float:
    t -= 1.0
    return t * t * t + 1.0

def ease_in_out(t: float) -> float:
    if t < 0.5:
        return 4.0 * t * t * t
    else:
        f = (2.0 * t) - 2.0
        return 0.5 * f * f * f + 1.0

_EASING_FUNCTIONS = {
    "linear": linear,
    "ease-in": ease_in,
    "ease-out": ease_out,
    "ease-in-out": ease_in_out,
}

def apply_easing(progress: float, easing_type: str = "linear") -> float:
    """Apply an easing function to a progress value [0.0, 1.0]."""
    progress = max(0.0, min(1.0, progress))
    func = _EASING_FUNCTIONS.get(easing_type, linear)
    return func(progress)
