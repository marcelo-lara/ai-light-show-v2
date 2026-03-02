import { initBackendState, applyPatch, applySnapshot } from "../shared/state/backend_state.ts";
import { initTheme } from "../shared/state/theme_state.ts";
import { WsClient } from "../shared/transport/ws_client.ts";
import type { ConnectionState, WsInbound } from "../shared/transport/protocol.ts";

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
  // 1) hydration/bootstrap
  const bootstrap = (window.__BOOTSTRAP_STATE__ ?? null) as any;
  if (bootstrap && typeof bootstrap === "object" && bootstrap.state) {
    initBackendState(bootstrap.state, { stale: true, seq: bootstrap.seq ?? 0 });
  } else {
    initBackendState(undefined, { stale: true, seq: 0 });
  }

  // 2) connect WS
  const ws = new WsClient(ctx.wsUrl, {
    onConnectionState: (s: ConnectionState) => {
      (globalThis as any).__WS_STATE__ = s;
    },
    onMessage: (m: WsInbound) => {
      if (m.type === "snapshot") applySnapshot(m);
      else if (m.type === "patch") applyPatch(m);
      else console.log("event:", m);
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
