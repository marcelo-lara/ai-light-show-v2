export type LlmStatus = "idle" | "streaming" | "error";

export type ChatRole = "user" | "assistant" | "system";

export type ChatMessage = {
  id: string;
  role: ChatRole;
  text: string;
  kind?: "info" | "error";
};

let state: { status: LlmStatus; lastError?: string; messages: ChatMessage[]; streamingText: string } = {
  status: "idle",
  messages: [],
  streamingText: "",
};
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
  state = { ...state, status, lastError };
  (globalThis as any).__LLM_STATE__ = state; // used by StatusCard model for now
  emit();
}

export function addUserMessage(text: string) {
  state = {
    ...state,
    messages: [...state.messages, { id: crypto.randomUUID(), role: "user", text }],
  };
  emit();
}

export function addAssistantMessage(text: string) {
  state = {
    ...state,
    messages: [...state.messages, { id: crypto.randomUUID(), role: "assistant", text }],
    status: "idle",
    streamingText: "",
  };
  emit();
}

export function addSystemMessage(text: string, kind: "info" | "error" = "info") {
  state = {
    ...state,
    status: kind === "error" ? "error" : state.status,
    messages: [...state.messages, { id: crypto.randomUUID(), role: "system", text, kind }],
  };
  emit();
}

export function appendStreamingChunk(chunk: string) {
  state = {
    ...state,
    status: "streaming",
    streamingText: `${state.streamingText}${chunk}`,
  };
  emit();
}

export function finishStreaming() {
  if (state.streamingText.trim().length > 0) {
    state = {
      ...state,
      messages: [...state.messages, { id: crypto.randomUUID(), role: "assistant", text: state.streamingText }],
      streamingText: "",
      status: "idle",
    };
  } else {
    state = { ...state, status: "idle" };
  }
  emit();
}
