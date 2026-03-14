import type { CueEntry } from "../../../../shared/transport/protocol.ts";

export function formatCueTime(time: number): string {
	return `${time.toFixed(2)}s`;
}

export function formatCueLabel(value: string): string {
	return value.replace(/[_-]+/g, " ").trim();
}

export function formatCueParams(data: Record<string, unknown>): string[] {
	const entries = Object.entries(data);
	if (entries.length === 0) return ["No parameters"];
	return entries.slice(0, 3).map(([key, value]) => `${formatCueLabel(key)}: ${String(value)}`);
}

export function cueSignature(cues: CueEntry[]): string {
	return cues
		.map((cue) => [cue.time, cue.fixture_id, cue.effect, cue.duration, JSON.stringify(cue.data)].join("|"))
		.join("~");
}

export function findCurrentCueIndex(cues: CueEntry[], timeMs: number): number {
	const timeSec = timeMs / 1000;
	for (let index = cues.length - 1; index >= 0; index -= 1) {
		if (cues[index].time <= timeSec) return index;
	}
	return -1;
}