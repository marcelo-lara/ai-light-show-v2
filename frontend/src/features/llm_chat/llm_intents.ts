import type { IntentMsg } from "../../shared/transport/protocol.ts";
import { setLlmStatus } from "./llm_state.ts";

function wsSend(msg: IntentMsg) {
  const ws = (globalThis as any).__WS_CLIENT__;
  if (!ws) return;
  ws.send(msg);
}

function reqId() {
  return crypto.randomUUID();
}

export function sendPrompt(prompt: string) {
  setLlmStatus("streaming");
  wsSend({
    type: "intent",
    req_id: reqId(),
    name: "llm.send_prompt",
    payload: { prompt },
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
