import type { Route } from "../shared/state/ui_state.ts";

export const ROUTES: Array<{ id: Route; label: string }> = [
  { id: "home", label: "Home" },
  { id: "song_analysis", label: "Song Analysis" },
  { id: "show_builder", label: "Show Builder" },
  { id: "dmx_control", label: "DMX Control" },
];
