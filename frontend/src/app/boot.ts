import { initBackendState, applyPatch, applySnapshot } from "../shared/state/backend_state.ts";
import { initTheme } from "../shared/state/theme_state.ts";
import { setWsState } from "../shared/state/ws_state.ts";
import { WsClient } from "../shared/transport/ws_client.ts";
import type { ConnectionState, WsInbound } from "../shared/transport/protocol.ts";
import { addAssistantMessage, addSystemMessage, appendStreamingChunk, cancelLlm, failLlm, finishStreaming } from "../features/llm_chat/llm_state.ts";

// If you inject bootstrap JSON in HTML, expose it as window.__BOOTSTRAP_STATE__
declare global {
  interface Window {
    __BOOTSTRAP_STATE__?: unknown;
  }
}

export type BootContext = {
  wsUrl: string; // e.g., "ws://localhost:8000/ws"
};

export function boot(ctx: BootContext) {
  initTheme(); // apply theme ASAP to avoid FOUC

  try {
    const ws = new URL(ctx.wsUrl);
    const protocol = ws.protocol === "wss:" ? "https:" : "http:";
    (globalThis as any).__BACKEND_HTTP_ORIGIN__ = `${protocol}//${ws.host}`;
  } catch {
    // ignore invalid ws url
  }

  // 1) hydration/bootstrap
  const injected = (window.__BOOTSTRAP_STATE__ ?? null) as any;
  let bootstrap = injected;

  if (!bootstrap?.state) {
    try {
      const raw = localStorage.getItem("last_snapshot");
      if (raw) bootstrap = JSON.parse(raw);
    } catch {
      // ignore storage parsing errors
    }
  }

  if (bootstrap && typeof bootstrap === "object" && bootstrap.state) {
    initBackendState(bootstrap.state, { stale: true, seq: Number(bootstrap.seq ?? 0) });
  } else {
    initBackendState(undefined, { stale: true, seq: 0 });
  }

  // 2) connect WS
  const ws = new WsClient(ctx.wsUrl, {
    onConnectionState: (s: ConnectionState) => {
      (globalThis as any).__WS_STATE__ = s;
      setWsState(s);
    },
    onMessage: (m: WsInbound) => {
      console.log("WS Dispatching Message:", m.type, m);
      if (m.type === "snapshot") {
        applySnapshot(m);
        try {
          localStorage.setItem("last_snapshot", JSON.stringify({ seq: m.seq, state: m.state }));
        } catch {
          // ignore storage errors
        }
      } else if (m.type === "patch") {
        applyPatch(m);
      } else if (m.type === "event") {
        const data = (m.data ?? {}) as Record<string, unknown>;
        if (data.domain === "llm" && typeof data.chunk === "string") {
          appendStreamingChunk(data.chunk);
          if (data.done === true) finishStreaming();
          return;
        }
        if (m.message === "llm_cancelled" && data.domain === "llm") {
          cancelLlm();
          return;
        }
        if (m.message === "llm_failed" && data.domain === "llm") {
          const error = typeof data.error === "string" ? data.error : "llm_request_failed";
          failLlm(error);
          addSystemMessage(`LLM request failed: ${error}`, "error");
          return;
        }
        if (m.message === "llm_rejected" && data.domain === "llm") {
          failLlm(typeof data.reason === "string" ? data.reason : "llm_rejected");
          addSystemMessage("LLM is unavailable while the show is running.", "error");
          return;
        }
        if (data.domain === "llm" && typeof data.message === "string") {
          addAssistantMessage(data.message);
          finishStreaming();
          return;
        }
        if (m.level === "error") {
          addSystemMessage(m.message, "error");
        }
        if (m.message === "cue_helper_applied") {
          const data = m.data as { helper_id?: string; generated?: number; replaced?: number; skipped?: number } | undefined;
          if (data) {
            const { helper_id, generated = 0, replaced = 0, skipped = 0 } = data;
            addSystemMessage(
              `Applied ${helper_id}: ${generated} generated, ${replaced} replaced, ${skipped} skipped`,
              "info"
            );
          }
        }
      }
    },
  });

  (globalThis as any).__WS_CLIENT__ = ws;

  ws.connect({
    type: "hello",
    client: "uix-ui",
    version: "0.1",
  });

  return ws;
}
