"""Process-wide configuration for the analyzer worker."""

from __future__ import annotations

import os

os.environ.setdefault("NUMBA_DISABLE_JIT", "1")

try:
    import numba

    numba.config.DISABLE_JIT = True
except Exception:
    pass
