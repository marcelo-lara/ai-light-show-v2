import { makeId } from "../../shared/utils/id.ts";

export type LlmStatus = "idle" | "waiting" | "streaming" | "error";

export type ChatRole = "user" | "assistant" | "system";

export type ChatMessage = {
  id: string;
  role: ChatRole;
  text: string;
  kind?: "info" | "error";
  source?: "llm-status";
};

let state: { status: LlmStatus; lastError?: string; messages: ChatMessage[]; streamingText: string } = {
  status: "idle",
  messages: [],
  streamingText: "",
};
(globalThis as any).__LLM_STATE__ = state;
const listeners = new Set<() => void>();

export function getLlmState() {
  return state;
}

export function subscribeLlmState(fn: () => void) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function emit() {
  (globalThis as any).__LLM_STATE__ = state;
  for (const fn of listeners) fn();
}

function commit(nextState: typeof state) {
  state = nextState;
  emit();
}

export function setLlmStatus(status: LlmStatus, lastError?: string) {
  commit({ ...state, status, lastError });
}

export function setLlmWaiting() {
  commit({ ...state, status: "waiting", lastError: undefined, streamingText: "" });
}

export function addUserMessage(text: string) {
  commit({
    ...state,
    messages: [...state.messages, { id: makeId(), role: "user", text }],
  });
}

export function addAssistantMessage(text: string) {
  commit({
    ...state,
    messages: [...state.messages, { id: makeId(), role: "assistant", text }],
    status: "idle",
    lastError: undefined,
    streamingText: "",
  });
}

export function addSystemMessage(text: string, kind: "info" | "error" = "info") {
  commit({
    ...state,
    status: kind === "error" ? "error" : state.status,
    messages: [...state.messages, { id: makeId(), role: "system", text, kind }],
  });
}

const LOW_VALUE_LOOKUP_MESSAGES = new Set(["Looking up song and fixture details"]);

export function addLlmLookupMessage(text: string) {
  const nextText = text.trim();
  if (!nextText) return;

  const messages = [...state.messages];
  const lastMessage = messages.at(-1);
  const nextIsLowValue = LOW_VALUE_LOOKUP_MESSAGES.has(nextText);

  if (lastMessage?.source === "llm-status") {
    if (lastMessage.text === nextText) {
      return;
    }
    const lastWasLowValue = LOW_VALUE_LOOKUP_MESSAGES.has(lastMessage.text);
    if (lastWasLowValue && !nextIsLowValue) {
      messages[messages.length - 1] = { ...lastMessage, text: nextText };
      commit({ ...state, messages });
      return;
    }
  }

  if (nextIsLowValue && messages.some((message) => message.source === "llm-status")) {
    return;
  }

  messages.push({
    id: makeId(),
    role: "system",
    text: nextText,
    kind: "info",
    source: "llm-status",
  });
  commit({ ...state, messages });
}

export function appendStreamingChunk(chunk: string) {
  commit({
    ...state,
    status: "streaming",
    lastError: undefined,
    streamingText: `${state.streamingText}${chunk}`,
  });
}

export function finishStreaming() {
  if (state.streamingText.trim().length > 0) {
    commit({
      ...state,
      messages: [...state.messages, { id: makeId(), role: "assistant", text: state.streamingText }],
      streamingText: "",
      status: "idle",
      lastError: undefined,
    });
  } else {
    commit({ ...state, status: "idle", lastError: undefined });
  }
}

export function failLlm(error: string) {
  commit({ ...state, status: "error", lastError: error, streamingText: "" });
}

export function cancelLlm() {
  commit({ ...state, status: "idle", lastError: undefined, streamingText: "" });
}

export function isLlmActiveStatus(status: LlmStatus) {
  return status === "waiting" || status === "streaming";
}
