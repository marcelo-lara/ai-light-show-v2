import { getBackendStore } from "../../../../shared/state/backend_state.ts";

export function formatTime(ms: number): string {
	return (ms / 1000).toFixed(3);
}

export function getFixtures() {
	return Object.values(getBackendStore().state.fixtures ?? {});
}

export function getPois() {
	return getBackendStore().state.pois ?? [];
}

export function getPlaybackTimeMs(): number {
	return getBackendStore().state.playback?.time_ms ?? 0;
}

export function getSupportedEffects(fixtureId: string): string[] {
	const fixtures = getBackendStore().state.fixtures ?? {};
	return fixtures[fixtureId]?.supported_effects ?? [];
}

export function getCueHelpers() {
	return getBackendStore().state.cue_helpers ?? [];
}
