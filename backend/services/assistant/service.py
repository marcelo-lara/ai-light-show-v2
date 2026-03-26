from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Dict

from .gateway import AssistantGatewayClient
from .interaction_log import AssistantInteractionLog
from .models import ActiveRequest, ConversationTurn, PendingAction
from .prompts import load_prompt


MAX_HISTORY_MESSAGES = 12


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
        self._conversation_history: Dict[str, list[ConversationTurn]] = {}

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

    async def clear_conversation(self, manager, payload: Dict[str, Any]) -> None:
        client_id = str(payload.get("_client_id") or "")
        if not client_id:
            return
        await self.cancel(manager, {"_client_id": client_id})
        self._conversation_history.pop(client_id, None)
        pending_keys = [key for key, pending in self._pending_actions.items() if pending.client_id == client_id]
        for key in pending_keys:
            self._pending_actions.pop(key, None)
        await self._interaction_log.write("conversation_cleared", client_id=client_id)
        await self._emit_client_event(client_id, manager, "info", "llm_conversation_cleared", {"domain": "llm", "cleared": True})

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
        self._conversation_history.pop(client_id, None)

    async def _run_prompt(self, manager, context: ActiveRequest) -> None:
        current_task = asyncio.current_task()
        messages = self._build_request_messages(manager, context.client_id, context.assistant_id, context.prompt)
        response_chunks: list[str] = []
        proposal_emitted = False
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
                if str(event.get("type") or "") == "delta":
                    response_chunks.append(str(event.get("delta") or ""))
                if str(event.get("type") or "") == "proposal":
                    proposal_emitted = True
                await self._forward_event(manager, context.client_id, context.request_id, context.assistant_id, event, context.prompt)
            assistant_text = "".join(response_chunks).strip()
            if assistant_text:
                self._append_conversation_turns(context.client_id, context.prompt, assistant_text)
                await self._interaction_log.write(
                    "conversation_history_appended",
                    request_id=context.request_id,
                    client_id=context.client_id,
                    user_prompt=context.prompt,
                    assistant_response=assistant_text,
                )
            elif not proposal_emitted:
                await self._interaction_log.write(
                    "conversation_history_skipped",
                    request_id=context.request_id,
                    client_id=context.client_id,
                    reason="empty_assistant_response",
                )
        except asyncio.CancelledError:
            await self._interaction_log.write("request_cancelled", request_id=context.request_id, client_id=context.client_id)
            await self._emit_client_event(context.client_id, manager, "info", "llm_cancelled", {"domain": "llm", "request_id": context.request_id})
        except Exception as exc:
            await self._interaction_log.write("request_failed", request_id=context.request_id, client_id=context.client_id, detail=str(exc))
            await self._emit_client_event(context.client_id, manager, "error", "llm_error", {"domain": "llm", "request_id": context.request_id, "code": "assistant_request_failed", "detail": str(exc), "retryable": True})
        finally:
            await self._interaction_log.write("request_finished", request_id=context.request_id, client_id=context.client_id)
            if self._requests.get(context.request_id) is current_task:
                self._requests.pop(context.request_id, None)
                self._active_by_client.pop(context.client_id, None)
            self._request_context.pop(context.request_id, None)

    async def _run_confirmed_action(self, manager, pending: PendingAction) -> None:
        current_task = asyncio.current_task()
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
            assistant_text = self._build_action_completion_text(pending, result)
            await self._interaction_log.write(
                "action_completion_generated",
                request_id=pending.request_id,
                client_id=pending.client_id,
                assistant_id=pending.assistant_id,
                completion=assistant_text,
            )
            if assistant_text:
                await self._emit_client_event(pending.client_id, manager, "info", "llm_delta", {"domain": "llm", "request_id": pending.request_id, "delta": assistant_text, "done": False})
                await self._emit_client_event(pending.client_id, manager, "info", "llm_done", {"domain": "llm", "request_id": pending.request_id, "finish_reason": "stop", "done": True})
                self._append_conversation_turns(pending.client_id, pending.prompt, assistant_text)
                await self._interaction_log.write(
                    "conversation_history_appended",
                    request_id=pending.request_id,
                    client_id=pending.client_id,
                    user_prompt=pending.prompt,
                    assistant_response=assistant_text,
                )
        except asyncio.CancelledError:
            await self._interaction_log.write("request_cancelled", request_id=pending.request_id, client_id=pending.client_id)
            await self._emit_client_event(pending.client_id, manager, "info", "llm_cancelled", {"domain": "llm", "request_id": pending.request_id})
        except Exception as exc:
            await self._interaction_log.write("request_failed", request_id=pending.request_id, client_id=pending.client_id, detail=str(exc))
            await self._emit_client_event(pending.client_id, manager, "error", "llm_error", {"domain": "llm", "request_id": pending.request_id, "code": "assistant_request_failed", "detail": str(exc), "retryable": True})
        finally:
            await self._interaction_log.write("request_finished", request_id=pending.request_id, client_id=pending.client_id)
            if self._requests.get(pending.request_id) is current_task:
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
        if pending.tool_name == "propose_cue_add_entries":
            entries = list(pending.arguments.get("entries") or [])
            added_entries: list[Dict[str, Any]] = []
            for entry in entries:
                result = await manager.state_manager.add_effect_cue_entry(
                    time=float(entry.get("time", 0.0)),
                    fixture_id=str(entry.get("fixture_id") or ""),
                    effect=str(entry.get("effect") or ""),
                    duration=float(entry.get("duration", 0.0) or 0.0),
                    data=entry.get("data") or {},
                )
                if not result.get("ok"):
                    return result
                added_entries.append(dict(result.get("entry") or {}))
            if added_entries:
                await manager._schedule_broadcast()
            return {"ok": True, "entries": added_entries, "count": len(added_entries)}
        if pending.tool_name == "propose_cue_clear_all":
            result = await manager.state_manager.clear_all_cue_entries()
            if result.get("ok"):
                await manager._schedule_broadcast()
            return result
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

    def _build_action_completion_text(self, pending: PendingAction, result: Dict[str, Any]) -> str:
        if pending.tool_name == "propose_cue_add_entries":
            entries = list(result.get("entries") or pending.arguments.get("entries") or [])
            if not entries:
                return "Added cue entries."
            fixture_ids = ", ".join(str(entry.get("fixture_id") or "") for entry in entries)
            effect_name = str(entries[0].get("effect") or "effect")
            time_value = float(entries[0].get("time", 0.0) or 0.0)
            return f"Added {effect_name} to {fixture_ids} at {time_value:.3f}s."
        if pending.tool_name == "propose_cue_clear_all":
            removed = int(result.get("removed", 0) or 0)
            return f"Cleared the cue sheet. Removed {removed} entries."
        if pending.tool_name == "propose_cue_clear_range":
            start_time = float(pending.arguments.get("start_time", 0.0))
            end_time = float(pending.arguments.get("end_time", start_time))
            removed = int(result.get("removed", 0) or 0)
            window_text = self._format_time_window(start_time, end_time)
            return f"Cleared cue items {window_text}. Removed {removed} entries."
        if pending.tool_name == "propose_chaser_apply":
            chaser_id = str(pending.arguments.get("chaser_id") or result.get("chaser_id") or "unknown_chaser")
            start_time = float(pending.arguments.get("start_time", 0.0))
            repetitions = int(pending.arguments.get("repetitions", 1) or 1)
            return f"Applied chaser {chaser_id} at {start_time:.3f}s for {repetitions} repetitions."
        return f"Completed {pending.tool_name}."

    def _format_time_window(self, start_time: float, end_time: float) -> str:
        if abs(end_time - start_time) < 1e-9:
            return f"at {start_time:.3f}s"
        return f"from {start_time:.3f}s to {end_time:.3f}s"

    def _build_request_messages(self, manager, client_id: str, assistant_id: str, prompt: str) -> list[Dict[str, Any]]:
        messages = [{"role": "system", "content": load_prompt(self._assistant_root, assistant_id)}]
        current_song = self._current_song_name(manager)
        if current_song:
            messages.append({"role": "system", "content": f"Current loaded song: {current_song}"})
        for turn in self._conversation_history.get(client_id, []):
            messages.append({"role": turn.role, "content": turn.content})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _append_conversation_turns(self, client_id: str, user_prompt: str, assistant_response: str) -> None:
        history = list(self._conversation_history.get(client_id, []))
        history.append(ConversationTurn(role="user", content=user_prompt))
        history.append(ConversationTurn(role="assistant", content=assistant_response))
        self._conversation_history[client_id] = history[-MAX_HISTORY_MESSAGES:]

    def _current_song_name(self, manager) -> str | None:
        if manager is None:
            return None
        current_song = getattr(getattr(manager, "state_manager", None), "current_song", None)
        song_id = getattr(current_song, "song_id", None)
        if song_id is None:
            return None
        text = str(song_id).strip()
        return text or None

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