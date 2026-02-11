"""Song Analyzer package initialization."""

import os

# Prevent numba JIT crashes in constrained container environments.
os.environ.setdefault("NUMBA_DISABLE_JIT", "1")