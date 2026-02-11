"""Numba configuration helpers."""

from __future__ import annotations

import os


def disable_numba_jit() -> None:
    """Disable numba JIT to avoid container crashes during librosa imports."""
    os.environ.setdefault("NUMBA_DISABLE_JIT", "1")
    try:
        import numba

        numba.config.DISABLE_JIT = True
    except Exception:
        # If numba is not available or fails to import, let callers proceed.
        pass
