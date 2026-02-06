# Compatibility shim: ensure typing_extensions exposes TypeAliasType
# Some installed packages (typing_inspection/pydantic) expect TypeAliasType to exist
# in typing_extensions; older typing_extensions builds may be missing it. Provide a
# minimal stand-in to avoid import-time errors in test environments.
try:
    import typing_extensions as _te
    # Backfill missing attributes expected by some installed packages.
    # Provide safe shims that mimic typing_extensions objects' callable behavior
    import types

    if not hasattr(_te, "TypeAliasType"):
        def TypeAliasType(*args, **kwargs):
            class _T: pass
            return _T
        _te.TypeAliasType = TypeAliasType

    if not hasattr(_te, "TypeIs"):
        def TypeIs(*args, **kwargs):
            class _T: pass
            return _T
        _te.TypeIs = TypeIs

    if not hasattr(_te, "LiteralString"):
        try:
            from typing import Literal as LiteralString  # best-effort substitute
            _te.LiteralString = LiteralString
        except Exception:
            _te.LiteralString = str

    if not hasattr(_te, "deprecated"):
        def deprecated(x):
            return x
        _te.deprecated = deprecated
except Exception:
    # Best-effort only; if this fails, downstream imports may still error.
    pass
