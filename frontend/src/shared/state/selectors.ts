import { getBackendStore } from "./backend_state.ts";

export function selectShowState(): string {
  const s = getBackendStore().state.system?.show_state;
  return s ?? "unknown";
}

export function selectEditLock(): boolean | null {
  const v = getBackendStore().state.system?.edit_lock;
  return typeof v === "boolean" ? v : null;
}

export function selectPlayback() {
  const p = getBackendStore().state.playback ?? {};
  return {
    state: p.state ?? "unknown",
    time_ms: p.time_ms ?? 0,
    bpm: p.bpm ?? null,
    section_name: p.section_name ?? null,
  };
}

export function selectFixtures() {
  return getBackendStore().state.fixtures ?? {};
}

export function selectArmedCount() {
  const fixtures = selectFixtures();
  const ids = Object.keys(fixtures);
  const armed = ids.filter((id) => fixtures[id]?.armed).length;
  return { armed, total: ids.length };
}
