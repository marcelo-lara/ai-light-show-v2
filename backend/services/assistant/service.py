from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict

from .gateway import AssistantGatewayClient
from .interaction_log import AssistantInteractionLog
from .models import ActiveRequest, PendingAction
from .prompts import load_prompt


class AssistantService:
    def __init__(self, backend_path: Path) -> None:
        self._assistant_root = backend_path / "services" / "assistant"
        self._gateway = AssistantGatewayClient(os.getenv("AGENT_GATEWAY_URL", "http://localhost:8090"))
        log_root = Path(os.getenv("ASSISTANT_LOG_DIR", str(backend_path / "logs" / "assistant")))
        self._interaction_log = AssistantInteractionLog(log_root)
        self._requests: Dict[str, asyncio.Task] = {}
        self._active_by_client: Dict[str, str] = {}
        self._pending_actions: Dict[tuple[str, str], PendingAction] = {}
        self._request_context: Dict[str, ActiveRequest] = {}

    async def submit(self, manager, payload: Dict[str, Any]) -> bool:
        prompt = str(payload.get("prompt") or "").strip()
        client_id = str(payload.get("_client_id") or "")
        request_id = str(payload.get("_req_id") or "")
        assistant_id = str(payload.get("assistant_id") or "generic")
        if not prompt or not client_id or not request_id:
            await self._emit_client_event(
                client_id,
                manager,
                "error",
                "llm_error",
                {"domain": "llm", "request_id": request_id, "code": "prompt_required", "detail": "Prompt is required.", "retryable": False},
            )
            return False
        await self._interaction_log.write(
            "request_received",
            request_id=request_id,
            client_id=client_id,
            assistant_id=assistant_id,
            prompt=prompt,
        )
        await self.cancel(manager, {"_client_id": client_id})
        self._request_context[request_id] = ActiveRequest(request_id=request_id, client_id=client_id, assistant_id=assistant_id, prompt=prompt)
        self._active_by_client[client_id] = request_id
        task = asyncio.create_task(self._run_prompt(manager, self._request_context[request_id]))
        self._requests[request_id] = task
        return False

    async def cancel(self, manager, payload: Dict[str, Any]) -> None:
        request_id = str(payload.get("request_id") or payload.get("_req_id") or "")
        client_id = str(payload.get("_client_id") or "")
        if not request_id and client_id:
            request_id = self._active_by_client.get(client_id, "")
        await self._interaction_log.write("request_cancel_requested", request_id=request_id or None, client_id=client_id or None)
        task = self._requests.pop(request_id, None)
        if task is not None:
            task.cancel()
        context = self._request_context.pop(request_id, None)
        if context is not None:
            self._active_by_client.pop(context.client_id, None)
            await self._emit_client_event(context.client_id, manager, "info", "llm_cancelled", {"domain": "llm", "request_id": request_id})

    async def confirm_action(self, manager, payload: Dict[str, Any]) -> None:
        request_id = str(payload.get("request_id") or "")
        action_id = str(payload.get("action_id") or "")
        pending = self._pending_actions.pop((request_id, action_id), None)
        if pending is None:
            await self._interaction_log.write("action_confirm_missing", request_id=request_id, action_id=action_id)
            await self._emit_client_event(str(payload.get("_client_id") or ""), manager, "error", "llm_error", {"domain": "llm", "request_id": request_id, "code": "unknown_action", "detail": "Pending action not found.", "retryable": False})
            return
        await self._interaction_log.write(
            "action_confirmed",
            request_id=request_id,
            action_id=action_id,
            client_id=pending.client_id,
            tool_name=pending.tool_name,
            arguments=pending.arguments,
        )
        self._active_by_client[pending.client_id] = request_id
        self._requests[request_id] = asyncio.create_task(self._run_confirmed_action(manager, pending))

    async def reject_action(self, manager, payload: Dict[str, Any]) -> None:
        request_id = str(payload.get("request_id") or "")
        action_id = str(payload.get("action_id") or "")
        pending = self._pending_actions.pop((request_id, action_id), None)
        client_id = pending.client_id if pending else str(payload.get("_client_id") or "")
        await self._interaction_log.write(
            "action_rejected",
            request_id=request_id,
            action_id=action_id,
            client_id=client_id,
            tool_name=pending.tool_name if pending else None,
        )
        await self._emit_client_event(client_id, manager, "info", "llm_action_rejected", {"domain": "llm", "request_id": request_id, "action_id": action_id})

    async def disconnect_client(self, client_id: str) -> None:
        request_id = self._active_by_client.pop(client_id, None)
        if request_id:
            await self._interaction_log.write("client_disconnected", client_id=client_id, request_id=request_id)
            task = self._requests.pop(request_id, None)
            if task is not None:
                task.cancel()
            self._request_context.pop(request_id, None)

    async def _run_prompt(self, manager, context: ActiveRequest) -> None:
        messages = [{"role": "system", "content": load_prompt(self._assistant_root, context.assistant_id)}, {"role": "user", "content": context.prompt}]
        await self._interaction_log.write(
            "gateway_request_started",
            request_id=context.request_id,
            client_id=context.client_id,
            assistant_id=context.assistant_id,
            messages=messages,
        )
        try:
            async for event in self._gateway.stream(messages, context.assistant_id):
                await self._interaction_log.write("gateway_event", request_id=context.request_id, client_id=context.client_id, payload=event)
                await self._forward_event(manager, context.client_id, context.request_id, context.assistant_id, event, context.prompt)
        except asyncio.CancelledError:
            await self._interaction_log.write("request_cancelled", request_id=context.request_id, client_id=context.client_id)
            await self._emit_client_event(context.client_id, manager, "info", "llm_cancelled", {"domain": "llm", "request_id": context.request_id})
        except Exception as exc:
            await self._interaction_log.write("request_failed", request_id=context.request_id, client_id=context.client_id, detail=str(exc))
            await self._emit_client_event(context.client_id, manager, "error", "llm_error", {"domain": "llm", "request_id": context.request_id, "code": "assistant_request_failed", "detail": str(exc), "retryable": True})
        finally:
            await self._interaction_log.write("request_finished", request_id=context.request_id, client_id=context.client_id)
            self._requests.pop(context.request_id, None)
            self._active_by_client.pop(context.client_id, None)
            self._request_context.pop(context.request_id, None)

    async def _run_confirmed_action(self, manager, pending: PendingAction) -> None:
        try:
            await self._emit_client_event(pending.client_id, manager, "info", "llm_status", {"domain": "llm", "request_id": pending.request_id, "phase": "applying_action", "label": f"Applying {pending.tool_name}", "assistant_id": pending.assistant_id})
            result = await self._apply_pending_action(manager, pending)
            await self._interaction_log.write(
                "action_result",
                request_id=pending.request_id,
                action_id=pending.action_id,
                client_id=pending.client_id,
                tool_name=pending.tool_name,
                result=result,
            )
            if not result.get("ok"):
                await self._emit_client_event(pending.client_id, manager, "error", "llm_error", {"domain": "llm", "request_id": pending.request_id, "code": "action_failed", "detail": str(result.get("reason") or result), "retryable": False})
                return
            await self._emit_client_event(pending.client_id, manager, "info", "llm_action_applied", {"domain": "llm", "request_id": pending.request_id, "action_id": pending.action_id, "tool_name": pending.tool_name})
            follow_up = self._build_follow_up_messages(pending, result)
            await self._interaction_log.write(
                "gateway_follow_up_started",
                request_id=pending.request_id,
                client_id=pending.client_id,
                assistant_id=pending.assistant_id,
                messages=follow_up,
            )
            async for event in self._gateway.stream(follow_up, pending.assistant_id):
                await self._interaction_log.write("gateway_event", request_id=pending.request_id, client_id=pending.client_id, payload=event)
                await self._forward_event(manager, pending.client_id, pending.request_id, pending.assistant_id, event)
        except asyncio.CancelledError:
            await self._interaction_log.write("request_cancelled", request_id=pending.request_id, client_id=pending.client_id)
            await self._emit_client_event(pending.client_id, manager, "info", "llm_cancelled", {"domain": "llm", "request_id": pending.request_id})
        except Exception as exc:
            await self._interaction_log.write("request_failed", request_id=pending.request_id, client_id=pending.client_id, detail=str(exc))
            await self._emit_client_event(pending.client_id, manager, "error", "llm_error", {"domain": "llm", "request_id": pending.request_id, "code": "assistant_request_failed", "detail": str(exc), "retryable": True})
        finally:
            await self._interaction_log.write("request_finished", request_id=pending.request_id, client_id=pending.client_id)
            self._requests.pop(pending.request_id, None)
            self._active_by_client.pop(pending.client_id, None)

    async def _forward_event(self, manager, client_id: str, request_id: str, assistant_id: str, event: Dict[str, Any], prompt: str | None = None) -> None:
        event_type = str(event.get("type") or "")
        if event_type == "status":
            await self._emit_client_event(client_id, manager, "info", "llm_status", {"domain": "llm", "request_id": request_id, "phase": event.get("phase"), "label": event.get("label"), "assistant_id": assistant_id})
            return
        if event_type == "delta":
            await self._emit_client_event(client_id, manager, "info", "llm_delta", {"domain": "llm", "request_id": request_id, "delta": event.get("delta", ""), "done": False})
            return
        if event_type == "done":
            await self._emit_client_event(client_id, manager, "info", "llm_done", {"domain": "llm", "request_id": request_id, "finish_reason": event.get("finish_reason", "stop"), "done": True})
            return
        if event_type == "proposal" and prompt is not None:
            action = PendingAction(request_id=request_id, client_id=client_id, assistant_id=assistant_id, prompt=prompt, action_id=str(event["action_id"]), tool_name=str(event["tool_name"]), arguments=dict(event.get("arguments") or {}), title=str(event.get("title") or "Confirm action"), summary=str(event.get("summary") or ""))
            self._pending_actions[(request_id, action.action_id)] = action
            await self._interaction_log.write(
                "action_proposed",
                request_id=request_id,
                action_id=action.action_id,
                client_id=client_id,
                tool_name=action.tool_name,
                arguments=action.arguments,
                title=action.title,
                summary=action.summary,
            )
            await self._emit_client_event(client_id, manager, "info", "llm_action_proposed", {"domain": "llm", "request_id": request_id, "action_id": action.action_id, "title": action.title, "summary": action.summary, "tool_name": action.tool_name, "arguments": action.arguments, "requires_confirmation": True})
            await self._emit_client_event(client_id, manager, "info", "llm_status", {"domain": "llm", "request_id": request_id, "phase": "awaiting_confirmation", "label": "Awaiting confirmation", "assistant_id": assistant_id})
            return
        if event_type == "error":
            await self._emit_client_event(client_id, manager, "error", "llm_error", {"domain": "llm", "request_id": request_id, "code": event.get("code", "gateway_error"), "detail": event.get("detail", "Assistant request failed."), "retryable": bool(event.get("retryable", True))})

    async def _apply_pending_action(self, manager, pending: PendingAction) -> Dict[str, Any]:
        if pending.tool_name == "propose_cue_clear_range":
            result = await manager.state_manager.clear_cue_entries(from_time=float(pending.arguments.get("start_time", 0.0)), to_time=float(pending.arguments.get("end_time", 0.0)))
            if result.get("ok"):
                await manager._schedule_broadcast()
            return result
        if pending.tool_name == "propose_chaser_apply":
            result = await manager.state_manager.apply_chaser(str(pending.arguments.get("chaser_id") or ""), float(pending.arguments.get("start_time", 0.0)) * 1000.0, int(pending.arguments.get("repetitions", 1) or 1))
            if result.get("ok"):
                await manager._schedule_broadcast()
            return result
        return {"ok": False, "reason": "unsupported_action"}

    def _build_follow_up_messages(self, pending: PendingAction, result: Dict[str, Any]) -> list[Dict[str, Any]]:
        prompt = load_prompt(self._assistant_root, pending.assistant_id)
        result_text = json.dumps({"tool_name": pending.tool_name, "arguments": pending.arguments, "result": result}, ensure_ascii=True)
        return [{"role": "system", "content": prompt}, {"role": "user", "content": pending.prompt}, {"role": "user", "content": f"The confirmed action has been executed. Tool result: {result_text}"}]

    async def _emit_client_event(self, client_id: str, manager, level: str, message: str, data: Dict[str, Any]) -> None:
        await self._interaction_log.write(
            "client_event",
            request_id=data.get("request_id"),
            client_id=client_id,
            level=level,
            message=message,
            data=data,
        )
        await manager.send_event_to_client(client_id, level, message, data)