import type { CueEntry } from "../../../../shared/transport/protocol.ts";
import { getCueSignatureToken } from "../../cue_utils.ts";

export function formatCueTime(time: number): string {
	return `${time.toFixed(3)}`;
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
	return cues.map(getCueSignatureToken).join("~");
}

export function findCurrentCueTime(cues: CueEntry[], timeMs: number): number | null {
	const timeSec = timeMs / 1000;
	for (let index = cues.length - 1; index >= 0; index -= 1) {
		if (cues[index].time <= timeSec) return cues[index].time;
	}
	return null;
}
