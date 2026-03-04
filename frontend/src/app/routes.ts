import type { Route } from "../shared/state/ui_state.ts";

export type RouteIcon = "wave" | "build" | "dmx" | "control";

export const ROUTES: Array<{ id: Route; label: string; icon: RouteIcon }> = [
  { id: "song_analysis", label: "Song Analysis", icon: "wave" },
  { id: "show_builder", label: "Show Builder", icon: "build" },
  { id: "dmx_control", label: "DMX Control", icon: "dmx" },
  { id: "show_control", label: "Show Control", icon: "control" },
];
