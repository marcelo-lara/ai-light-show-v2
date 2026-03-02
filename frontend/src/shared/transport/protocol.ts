// Protocol types for WS messages.
// Keep this file as the single source of truth for message shapes.

export type WsInbound =
  | SnapshotMsg
  | PatchMsg
  | EventMsg;

export type WsOutbound =
  | HelloMsg
  | IntentMsg;

export type ConnectionState =
  | "disconnected"
  | "connecting"
  | "connected"
  | "reconnecting";

export type SnapshotMsg = {
  type: "snapshot";
  seq: number;
  state: BackendState;
};

export type PatchMsg = {
  type: "patch";
  seq: number;
  changes: Array<{ path: (string | number)[]; value: unknown }>;
};

export type EventMsg = {
  type: "event";
  level: "info" | "warning" | "error";
  message: string;
  data?: unknown;
};

export type HelloMsg = {
  type: "hello";
  client: "uix-ui";
  version: string;
};

export type IntentMsg = {
  type: "intent";
  req_id: string;
  name: IntentName;
  payload: Record<string, unknown>;
};

export type IntentName =
  | "transport.play"
  | "transport.pause"
  | "transport.stop"
  | "transport.jump_to_time"
  | "transport.jump_to_section"
  | "fixture.set_arm"
  | "fixture.set_values"
  | "fixture.preview_effect"
  | "fixture.stop_preview"
  | "llm.send_prompt"
  | "llm.cancel";

export type BackendState = {
  // Backend authoritative, do not infer in frontend.
  system?: {
    show_state?: "running" | "idle" | string; // allow forward compatibility
    edit_lock?: boolean;
  };
  playback?: {
    state?: "playing" | "paused" | "stopped" | string;
    time_ms?: number;
    bpm?: number;
    section_name?: string;
  };
  fixtures?: Record<string, FixtureState>;
  // Add other domains as backend evolves: analysis, show_builder, pois, etc.
};

export type FixtureState = {
  id: string;
  type?: string; // "moving_head" | "rgb" | ...
  name?: string;
  group?: string;
  armed?: boolean;
  values?: Record<string, number>; // semantic values if backend provides them
  channels?: Record<string, number>; // raw channel values if backend provides them
  capabilities?: Record<string, unknown>; // optional: backend-declared capabilities
};
