export type Route = "home" | "song_analysis" | "show_builder" | "dmx_control";

export type UiState = {
  route: Route;
  selectedFixtureId?: string;
};

const ROUTE_KEY = "ui_route";

function readRoute(): Route {
  try {
    const value = localStorage.getItem(ROUTE_KEY);
    if (value === "home" || value === "song_analysis" || value === "show_builder" || value === "dmx_control") {
      return value;
    }
  } catch {
    // ignore
  }
  return "home";
}

let ui: UiState = { route: readRoute() };
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
  try {
    localStorage.setItem(ROUTE_KEY, route);
  } catch {
    // ignore
  }
  emit();
}

export function setSelectedFixtureId(id?: string) {
  ui = { ...ui, selectedFixtureId: id };
  emit();
}
