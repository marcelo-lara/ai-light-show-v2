from __future__ import annotations

from typing import Any, Dict


def _result(ok: bool, level: str, message: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return {"ok": ok, "level": level, "message": message, "data": data}


async def execute_add_cue(manager, payload: Dict[str, Any]) -> Dict[str, Any]:
    time = payload.get("time")
    fixture_id = str(payload.get("fixture_id") or "")
    effect = str(payload.get("effect") or "")
    chaser_id = str(payload.get("chaser_id") or "")
    duration = payload.get("duration", 0.0)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    if time is None:
        return _result(False, "error", "cue_add_failed", {"reason": "missing_time"})
    try:
        time_f = float(time)
    except (TypeError, ValueError):
        return _result(False, "error", "cue_add_failed", {"reason": "invalid_time"})
    if bool(chaser_id) == bool(effect or fixture_id):
        return _result(False, "error", "cue_add_failed", {"reason": "invalid_cue_shape"})
    if chaser_id:
        result = await manager.state_manager.add_chaser_cue_entry(time=time_f, chaser_id=chaser_id, data=data)
        return _result(bool(result.get("ok")), "info" if result.get("ok") else "error", "cue_added" if result.get("ok") else "cue_add_failed", result)
    if not fixture_id:
        return _result(False, "error", "cue_add_failed", {"reason": "missing_fixture_id"})
    if not effect:
        return _result(False, "error", "cue_add_failed", {"reason": "missing_effect"})
    try:
        duration_f = max(0.0, float(duration))
    except (TypeError, ValueError):
        duration_f = 0.0
    result = await manager.state_manager.add_effect_cue_entry(
        time=time_f,
        fixture_id=fixture_id,
        effect=effect,
        duration=duration_f,
        data=data,
    )
    return _result(bool(result.get("ok")), "info" if result.get("ok") else "error", "cue_added" if result.get("ok") else "cue_add_failed", result)


async def execute_update_cue(manager, payload: Dict[str, Any]) -> Dict[str, Any]:
    index = payload.get("index")
    patch = payload.get("patch") or {}
    if index is None:
        return _result(False, "error", "cue_update_failed", {"reason": "missing_index"})
    try:
        index_i = int(index)
    except (TypeError, ValueError):
        return _result(False, "error", "cue_update_failed", {"reason": "invalid_index"})
    if not isinstance(patch, dict) or not patch:
        return _result(False, "error", "cue_update_failed", {"reason": "missing_patch"})
    result = await manager.state_manager.update_cue_entry(index_i, patch)
    return _result(bool(result.get("ok")), "info" if result.get("ok") else "error", "cue_updated" if result.get("ok") else "cue_update_failed", result)


async def execute_delete_cue(manager, payload: Dict[str, Any]) -> Dict[str, Any]:
    index = payload.get("index")
    if index is None:
        return _result(False, "error", "cue_delete_failed", {"reason": "missing_index"})
    try:
        index_i = int(index)
    except (TypeError, ValueError):
        return _result(False, "error", "cue_delete_failed", {"reason": "invalid_index"})
    result = await manager.state_manager.delete_cue_entry(index_i)
    return _result(bool(result.get("ok")), "info" if result.get("ok") else "error", "cue_deleted" if result.get("ok") else "cue_delete_failed", result)