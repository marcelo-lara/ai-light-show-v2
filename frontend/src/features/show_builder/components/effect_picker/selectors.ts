import { getBackendStore } from "../../../../shared/state/backend_state.ts";
import type { ChaserDefinition } from "../../../../shared/transport/protocol.ts";
import { getSupportedEffectIds } from "../../../../shared/transport/supported_effects.ts";

export function formatTime(ms: number): string {
	return (ms / 1000).toFixed(3);
}

export function getFixtures() {
	return Object.values(getBackendStore().state.fixtures ?? {});
}

export function getFixtureType(fixtureId: string): string | undefined {
	const fixtures = getBackendStore().state.fixtures ?? {};
	return fixtures[fixtureId]?.type;
}

export function getPois() {
	return getBackendStore().state.pois ?? [];
}

export function getPlaybackTimeMs(): number {
	return getBackendStore().state.playback?.time_ms ?? 0;
}

export function getSongBpm(): number {
	return Number(getBackendStore().state.playback?.bpm ?? getBackendStore().state.song?.bpm ?? 0);
}

export function getSupportedEffects(fixtureId: string): string[] {
	const fixtures = getBackendStore().state.fixtures ?? {};
	return getSupportedEffectIds(fixtures[fixtureId]?.supported_effects);
}

export function getCueHelpers() {
	return getBackendStore().state.cue_helpers ?? [];
}

export function getChasers(): ChaserDefinition[] {
	return getBackendStore().state.chasers ?? [];
}
