from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from api.intents.cue.mutate_rows import execute_add_cue, execute_delete_cue, execute_update_cue
from api.intents.cue.mutate_sheet import execute_apply_helper, execute_clear_cue


router = APIRouter()


class CueEditRequest(BaseModel):
    payload: Dict[str, Any] = Field(default_factory=dict)


def _event_from_result(result: Dict[str, Any]) -> Dict[str, Any]:
    return {"level": result["level"], "message": result["message"], "data": result["data"]}


def _success_answer(intent_name: str, event: Dict[str, Any]) -> str:
    data = event.get("data") or {}
    if intent_name == "cue.clear":
        removed = int(data.get("removed") or 0)
        remaining = int(data.get("remaining") or 0)
        return f"Cleared {removed} cue rows. {remaining} cue rows remain."
    if intent_name == "cue.add":
        return "Cue row added successfully."
    if intent_name == "cue.update":
        return "Cue row updated successfully."
    if intent_name == "cue.delete":
        return "Cue row deleted successfully."
    if intent_name == "cue.apply_helper":
        generated = int(data.get("generated") or 0)
        replaced = int(data.get("replaced") or 0)
        skipped = int(data.get("skipped") or 0)
        return f"Applied cue helper. Generated {generated}, replaced {replaced}, skipped {skipped}."
    return "Cue edit completed successfully."


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
    return {
        "ok": True,
        "data": {
            "intent": intent_name,
            "event": event,
            "answer": _success_answer(intent_name, event),
        },
    }


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