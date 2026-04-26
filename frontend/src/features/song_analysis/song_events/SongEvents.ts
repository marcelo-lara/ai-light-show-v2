import type { SongAnalysisEvent } from "../../../shared/transport/protocol.ts";

export type SongEvent = {
	id: string;
	type: string;
	startTime: number;
	endTime: number;
	confidence: number;
	intensity: number;
	sectionId: string;
	sectionName: string | null;
	provenance: string;
	summary: string;
	createdBy: string;
	evidenceSummary: string;
	lightingHint: string;
};

function toNumber(value: unknown): number {
	const picked = Number(value);
	return Number.isFinite(picked) ? picked : 0;
}

export class SongEvents {
	readonly items: SongEvent[];

	constructor(items: SongEvent[]) {
		this.items = items;
	}

	static fromAnalysis(rows: SongAnalysisEvent[]): SongEvents {
		const items: SongEvent[] = [];
		for (const row of rows) {
			if (!row || typeof row !== "object") continue;
			const id = String(row.id ?? "").trim();
			const type = String(row.type ?? "").trim();
			const startTime = toNumber(row.start_time);
			const endTime = toNumber(row.end_time);
			if (!id || !type || endTime <= startTime) continue;
			items.push({
				id,
				type,
				startTime,
				endTime,
				confidence: toNumber(row.confidence),
				intensity: toNumber(row.intensity),
				sectionId: String(row.section_id ?? "").trim(),
				sectionName: row.section_name == null ? null : String(row.section_name).trim(),
				provenance: String(row.provenance ?? "").trim(),
				summary: String(row.summary ?? "").trim(),
				createdBy: String(row.created_by ?? "").trim(),
				evidenceSummary: String(row.evidence_summary ?? "").trim(),
				lightingHint: String(row.lighting_hint ?? "").trim(),
			});
		}
		items.sort((left, right) => left.startTime - right.startTime || left.endTime - right.endTime || left.id.localeCompare(right.id));
		return new SongEvents(items);
	}

	activeIndexes(timeMs: number): number[] {
		if (!Number.isFinite(timeMs)) return [];
		const cursorS = Math.max(0, timeMs / 1000);
		const matches: number[] = [];
		for (let index = 0; index < this.items.length; index++) {
			const item = this.items[index];
			if (cursorS >= item.startTime && cursorS < item.endTime) matches.push(index);
		}
		return matches;
	}

	activeIndex(timeMs: number): number {
		return this.activeIndexes(timeMs)[0] ?? -1;
	}

	isActive(index: number, timeMs: number): boolean {
		return this.activeIndexes(timeMs).includes(index);
	}
}