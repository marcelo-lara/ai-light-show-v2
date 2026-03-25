import { makeId } from "../../shared/utils/id.ts";

export type LlmStatus = "idle" | "streaming" | "awaiting-confirmation" | "error";

export type ChatRole = "user" | "assistant" | "system";

export type PendingAction = {
  requestId: string;
  actionId: string;
  title: string;
  summary: string;
  toolName?: string;
  arguments?: Record<string, unknown>;
};

export type ChatMessage = {
  id: string;
  role: ChatRole;
  text: string;
  kind?: "info" | "error" | "status" | "proposal";
  requestId?: string;
  action?: PendingAction;
};

let state: {
  status: LlmStatus;
  lastError?: string;
  messages: ChatMessage[];
  streamingText: string;
  activeRequestId?: string;
} = {
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

export function beginLlmRequest(requestId: string) {
  state = {
    ...state,
    activeRequestId: requestId,
    status: "streaming",
    streamingText: "",
    lastError: undefined,
  };
  emit();
}

export function addUserMessage(text: string) {
  state = {
    ...state,
    messages: [...state.messages, { id: makeId(), role: "user", text }],
  };
  emit();
}

export function addAssistantMessage(text: string) {
  state = {
    ...state,
    messages: [...state.messages, { id: makeId(), role: "assistant", text }],
    status: "idle",
    streamingText: "",
    activeRequestId: undefined,
  };
  emit();
}

export function addSystemMessage(text: string, kind: "info" | "error" = "info") {
  state = {
    ...state,
    status: kind === "error" ? "error" : state.status,
    messages: [...state.messages, { id: makeId(), role: "system", text, kind }],
  };
  emit();
}

export function upsertSystemStatus(requestId: string, text: string) {
  const lastMessage = state.messages.at(-1);
  if (
    lastMessage?.role === "system" &&
    lastMessage.kind === "status" &&
    lastMessage.requestId === requestId &&
    lastMessage.text === text
  ) {
    state = { ...state, status: "streaming", activeRequestId: requestId };
    emit();
    return;
  }
  state = {
    ...state,
    status: "streaming",
    activeRequestId: requestId,
    messages: [...state.messages, { id: makeId(), role: "system", text, kind: "status", requestId }],
  };
  emit();
}

export function addActionProposal(action: PendingAction) {
  state = {
    ...state,
    status: "awaiting-confirmation",
    activeRequestId: action.requestId,
    messages: [
      ...state.messages,
      {
        id: makeId(),
        role: "system",
        text: action.summary,
        kind: "proposal",
        requestId: action.requestId,
        action,
      },
    ],
  };
  emit();
}

export function resolveActionProposal(requestId: string, actionId: string, text: string, kind: "info" | "error" = "info") {
  state = {
    ...state,
    status: kind === "error" ? "error" : "idle",
    activeRequestId: kind === "error" ? requestId : undefined,
    messages: state.messages.map((message) => {
      if (message.kind !== "proposal" || message.requestId !== requestId || message.action?.actionId !== actionId) {
        return message;
      }
      return { ...message, text, kind, action: undefined };
    }),
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
      messages: [...state.messages, { id: makeId(), role: "assistant", text: state.streamingText }],
      streamingText: "",
      status: "idle",
      activeRequestId: undefined,
    };
  } else {
    state = { ...state, status: "idle", activeRequestId: undefined };
  }
  emit();
}

export function failStreaming(requestId: string | undefined, code: string, detail: string) {
  state = {
    ...state,
    status: "error",
    lastError: code,
    activeRequestId: requestId,
    streamingText: "",
    messages: [...state.messages, { id: makeId(), role: "system", text: detail, kind: "error", requestId }],
  };
  emit();
}
