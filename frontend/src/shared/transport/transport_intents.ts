import type { IntentMsg } from "./protocol.ts";
import { makeId } from "../utils/id.ts";

function wsSend(msg: IntentMsg) {
  const ws = (globalThis as any).__WS_CLIENT__;
  if (!ws) return;
  ws.send(msg);
}

function reqId() {
  return makeId();
}

export function transportPlay() {
  wsSend({
    type: "intent",
    req_id: reqId(),
    name: "transport.play",
    payload: {},
  });
}

export function transportPause() {
  wsSend({
    type: "intent",
    req_id: reqId(),
    name: "transport.pause",
    payload: {},
  });
}

export function transportStop() {
  wsSend({
    type: "intent",
    req_id: reqId(),
    name: "transport.stop",
    payload: {},
  });
}

export function transportJumpToTime(timeMs: number) {
  wsSend({
    type: "intent",
    req_id: reqId(),
    name: "transport.jump_to_time",
    payload: { time_ms: Math.max(0, Math.round(timeMs)) },
  });
}

export function transportJumpToSection(sectionIndex: number) {
  wsSend({
    type: "intent",
    req_id: reqId(),
    name: "transport.jump_to_section",
    payload: { section_index: Math.max(0, Math.floor(sectionIndex)) },
  });
}
