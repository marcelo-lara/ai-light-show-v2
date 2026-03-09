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
  | "llm.cancel"
  | "poi.create"
  | "poi.update"
  | "poi.delete"
  | "poi.update_fixture_target";

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
  song?: SongState | null;
  pois?: Poi[];
  // Add other domains as backend evolves: analysis, show_builder, pois, etc.
};

export type Poi = {
  id: string;
  name: string;
  location: {
    x: number;
    y: number;
    z: number;
  };
};

export type SongState = {
  filename?: string;
  audio_url?: string | null;
  length_s?: number | null;
  bpm?: number | null;
  sections?: SongSection[];
  beats?: number[];
  downbeats?: number[];
};

export type SongSection = {
  name: string;
  start_s: number;
  end_s: number;
};

export type FixtureState = {
  id: string;
  type?: string; // "moving_head" | "rgb" | ...
  name?: string;
  group?: string;
  armed?: boolean;
  values?: Record<string, number | string>; // semantic values from backend
  capabilities?: Record<string, boolean>; // e.g. { pan_tilt: true, rgb: true }
  meta_channels?: Record<string, MetaChannel>;
  mappings?: Record<string, Record<string, number | string>>;
};

export type MetaChannel = {
  kind: "u8" | "u16" | "rgb" | "enum";
  label: string;
  channel?: string; // name of raw channel
  channels?: string[]; // names for u16/rgb
  mapping?: string; // mapping id for enum
  step?: boolean; // UI hint: discrete stepped selector
  hidden?: boolean; // UI hint: do not render control in default views
  min?: number;
  max?: number;
  arm?: number;
};
