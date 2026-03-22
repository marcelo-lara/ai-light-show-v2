import type { ConnectionState } from "../transport/protocol.ts";

let state: ConnectionState = "disconnected";
const listeners = new Set<() => void>();

export function getWsState(): ConnectionState {
  return state;
}

export function subscribeWsState(fn: () => void) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function setWsState(next: ConnectionState) {
  if (state === next) return;
  state = next;
  for (const fn of listeners) fn();
}