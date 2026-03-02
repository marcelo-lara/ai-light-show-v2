import type { IntentMsg } from "../../shared/transport/protocol.ts";
import { addSystemMessage, addUserMessage, setLlmStatus } from "./llm_state.ts";

function wsSend(msg: IntentMsg) {
  const ws = (globalThis as any).__WS_CLIENT__;
  if (!ws) return;
  ws.send(msg);
}

function reqId() {
  return crypto.randomUUID();
}

export function sendPrompt(prompt: string) {
  if (!prompt.trim()) return;
  addUserMessage(prompt.trim());
  setLlmStatus("streaming");
  if (!(globalThis as any).__WS_CLIENT__) {
    addSystemMessage("WebSocket is not connected.", "error");
    setLlmStatus("error", "not_connected");
    return;
  }

  wsSend({
    type: "intent",
    req_id: reqId(),
    name: "llm.send_prompt",
    payload: { prompt: prompt.trim() },
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
