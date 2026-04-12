import type { SongAnalysisPattern } from "../../../shared/transport/protocol.ts";

export type ChordPatternOccurrence = {
	startBar: number;
	endBar: number;
	startTime: number;
	endTime: number;
	mismatchCount: number;
	sequence: string;
};

export type ChordPattern = {
	id: string;
	label: string;
	barCount: number;
	sequence: string;
	occurrenceCount: number;
	occurrences: ChordPatternOccurrence[];
};

function toNumber(value: unknown): number {
	const picked = Number(value);
	return Number.isFinite(picked) ? picked : 0;
}

export class ChordPatterns {
	readonly items: ChordPattern[];

	constructor(items: ChordPattern[]) {
		this.items = items;
	}

	static fromAnalysis(rows: SongAnalysisPattern[]): ChordPatterns {
		const items: ChordPattern[] = [];
		for (const row of rows) {
			if (!row || typeof row !== "object") continue;
			const id = String(row.id ?? "").trim();
			const label = String(row.label ?? "").trim();
			const sequence = String(row.sequence ?? "").trim();
			const barCount = Math.max(0, Math.trunc(toNumber(row.bar_count)));
			if (!id || !label || !sequence || barCount <= 0) continue;
			const occurrences = (row.occurrences ?? [])
				.map((occurrence) => ({
					startBar: Math.trunc(toNumber(occurrence.start_bar)),
					endBar: Math.trunc(toNumber(occurrence.end_bar)),
					startTime: toNumber(occurrence.start_s),
					endTime: toNumber(occurrence.end_s),
					mismatchCount: Math.max(0, Math.trunc(toNumber(occurrence.mismatch_count))),
					sequence: String(occurrence.sequence ?? "").trim(),
				}))
				.filter((occurrence) => occurrence.endBar > occurrence.startBar && occurrence.endTime > occurrence.startTime)
				.sort((left, right) => left.startTime - right.startTime || left.endTime - right.endTime || left.startBar - right.startBar);
			if (!occurrences.length) continue;
			items.push({
				id,
				label,
				barCount,
				sequence,
				occurrenceCount: occurrences.length,
				occurrences,
			});
		}
		items.sort((left, right) => right.occurrenceCount - left.occurrenceCount || left.label.localeCompare(right.label) || left.id.localeCompare(right.id));
		return new ChordPatterns(items);
	}

	activeOccurrenceKeys(timeMs: number): Set<string> {
		if (!Number.isFinite(timeMs)) return new Set<string>();
		const cursorS = Math.max(0, timeMs / 1000);
		const keys = new Set<string>();
		for (let patternIndex = 0; patternIndex < this.items.length; patternIndex++) {
			const pattern = this.items[patternIndex];
			for (let occurrenceIndex = 0; occurrenceIndex < pattern.occurrences.length; occurrenceIndex++) {
				const occurrence = pattern.occurrences[occurrenceIndex];
				if (cursorS >= occurrence.startTime && cursorS < occurrence.endTime) keys.add(`${patternIndex}:${occurrenceIndex}`);
			}
		}
		return keys;
	}
}