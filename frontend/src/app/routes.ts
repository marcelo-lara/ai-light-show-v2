import type { Route } from "../shared/state/ui_state.ts";
import type { IconName } from "../shared/svg_icons/index.ts";

export type RouteIcon = IconName;

export const ROUTES: Array<{ id: Route; label: string; icon: RouteIcon }> = [
  { id: "show_control", label: "Show Control", icon: "dashboard" },
  { id: "song_analysis", label: "Song Analysis", icon: "waveSignalMonitor" },
  { id: "show_builder", label: "Show Builder", icon: "addSong" },
  { id: "dmx_control", label: "DMX Control", icon: "equalizer" },
];
