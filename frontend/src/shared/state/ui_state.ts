export type Route = "home" | "song_analysis" | "show_builder" | "dmx_control";

export type UiState = {
  route: Route;
  selectedFixtureId?: string;
};

let ui: UiState = { route: "home" };
const listeners = new Set<() => void>();

export function getUiState(): UiState {
  return ui;
}

export function subscribeUiState(fn: () => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

function emit() {
  for (const fn of listeners) fn();
}

export function setRoute(route: Route) {
  ui = { ...ui, route };
  emit();
}

export function setSelectedFixtureId(id?: string) {
  ui = { ...ui, selectedFixtureId: id };
  emit();
}
