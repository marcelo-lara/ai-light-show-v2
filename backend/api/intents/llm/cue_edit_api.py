from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from api.intents.cue.mutate_rows import execute_add_cue, execute_delete_cue, execute_update_cue
from api.intents.cue.mutate_sheet import execute_apply_helper, execute_clear_cue
from api.intents.llm.cue_sheet_context import build_cue_sheet_payload


router = APIRouter()


class CueEditRequest(BaseModel):
    payload: Dict[str, Any] = Field(default_factory=dict)


def _event_from_result(result: Dict[str, Any]) -> Dict[str, Any]:
    return {"level": result["level"], "message": result["message"], "data": result["data"]}


async def _run_cue_edit(request: Request, intent_name: str, payload: Dict[str, Any], executor) -> Dict[str, Any]:
    manager = request.app.state.ws_manager
    if await manager.state_manager.get_is_playing():
        event = {"level": "warning", "message": "llm_cue_edit_rejected", "data": {"intent": intent_name, "reason": "show_running"}}
        await manager.broadcast_event(event["level"], event["message"], event["data"])
        return {"ok": False, "error": event}
    result = await executor(manager, payload if isinstance(payload, dict) else {})
    event = _event_from_result(result)
    await manager.broadcast_event(event["level"], event["message"], event["data"])
    if not result["ok"]:
        return {"ok": False, "error": {"intent": intent_name, "event": event}}
    await manager._schedule_broadcast()
    return {"ok": True, "data": {"intent": intent_name, "event": event, "cue_sheet": build_cue_sheet_payload(manager)}}


@router.post("/llm/actions/cues/add")
async def llm_add_cue(request: Request, body: CueEditRequest):
    return await _run_cue_edit(request, "cue.add", body.payload, execute_add_cue)


@router.post("/llm/actions/cues/update")
async def llm_update_cue(request: Request, body: CueEditRequest):
    return await _run_cue_edit(request, "cue.update", body.payload, execute_update_cue)


@router.post("/llm/actions/cues/delete")
async def llm_delete_cue(request: Request, body: CueEditRequest):
    return await _run_cue_edit(request, "cue.delete", body.payload, execute_delete_cue)


@router.post("/llm/actions/cues/clear")
async def llm_clear_cues(request: Request, body: CueEditRequest):
    return await _run_cue_edit(request, "cue.clear", body.payload, execute_clear_cue)


@router.post("/llm/actions/cues/apply-helper")
async def llm_apply_cue_helper(request: Request, body: CueEditRequest):
    return await _run_cue_edit(request, "cue.apply_helper", body.payload, execute_apply_helper)