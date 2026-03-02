export type LlmStatus = "idle" | "streaming" | "error";

let state: { status: LlmStatus; lastError?: string } = { status: "idle" };
const listeners = new Set<() => void>();

export function getLlmState() {
  return state;
}

export function subscribeLlmState(fn: () => void) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function emit() {
  for (const fn of listeners) fn();
}

export function setLlmStatus(status: LlmStatus, lastError?: string) {
  state = { status, lastError };
  (globalThis as any).__LLM_STATE__ = state; // used by StatusCard model for now
  emit();
}
