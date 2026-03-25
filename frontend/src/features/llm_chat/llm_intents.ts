import type { IntentMsg } from "../../shared/transport/protocol.ts";
import { addSystemMessage, addUserMessage, beginLlmRequest, clearConversationState, resolveActionProposal, setLlmStatus } from "./llm_state.ts";
import { makeId } from "../../shared/utils/id.ts";

function wsSend(msg: IntentMsg) {
  const ws = (globalThis as any).__WS_CLIENT__;
  if (!ws) return;
  ws.send(msg);
}

function reqId() {
  return makeId();
}

export function sendPrompt(prompt: string) {
  if (!prompt.trim()) return;
  const requestId = reqId();
  addUserMessage(prompt.trim());
  beginLlmRequest(requestId);
  if (!(globalThis as any).__WS_CLIENT__) {
    addSystemMessage("WebSocket is not connected.", "error");
    setLlmStatus("error", "not_connected");
    return;
  }

  wsSend({
    type: "intent",
    req_id: requestId,
    name: "llm.send_prompt",
    payload: { prompt: prompt.trim(), assistant_id: "generic" },
  });
}

export function cancelPrompt() {
  wsSend({
    type: "intent",
    req_id: reqId(),
    name: "llm.cancel",
    payload: {},
  });
}

export function clearConversation() {
  if (!(globalThis as any).__WS_CLIENT__) {
    clearConversationState();
    return;
  }
  wsSend({
    type: "intent",
    req_id: reqId(),
    name: "llm.clear_conversation",
    payload: {},
  });
}

export function confirmAction(requestId: string, actionId: string) {
  resolveActionProposal(requestId, actionId, "Applying action...", "info");
  wsSend({
    type: "intent",
    req_id: reqId(),
    name: "llm.confirm_action",
    payload: { request_id: requestId, action_id: actionId },
  });
}

export function rejectAction(requestId: string, actionId: string) {
  resolveActionProposal(requestId, actionId, "Action rejected.", "info");
  wsSend({
    type: "intent",
    req_id: reqId(),
    name: "llm.reject_action",
    payload: { request_id: requestId, action_id: actionId },
  });
}
