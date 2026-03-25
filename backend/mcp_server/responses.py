from __future__ import annotations

from typing import Any, Dict, Optional


def ok(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"ok": True, "data": data}


def fail(code: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    error: Dict[str, Any] = {"code": code, "message": message}
    if details:
        error["details"] = details
    return {"ok": False, "error": error}