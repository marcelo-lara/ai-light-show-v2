let currentTimeMs = 0;

export function getSongPlayerTimeMs(): number {
	return currentTimeMs;
}

export function setSongPlayerTimeMs(timeMs: number): void {
	currentTimeMs = Number.isFinite(timeMs) ? Math.max(0, timeMs) : 0;
}