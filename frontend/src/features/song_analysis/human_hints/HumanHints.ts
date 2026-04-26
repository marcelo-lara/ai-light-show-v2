import type { SongHumanHint, SongHumanHintsStatus } from "../../../shared/transport/protocol.ts";

export type HumanHint = {
	id: string;
	startTime: number;
	endTime: number;
	title: string;
	summary: string;
	lightingHint: string;
};

export type HumanHintsStatus = {
	dirty: boolean;
	saved: boolean;
	fileExists: boolean;
};

function toNumber(value: unknown, fallback = 0): number {
	const picked = Number(value);
	return Number.isFinite(picked) && picked >= 0 ? picked : fallback;
}

export function readHumanHints(rows: SongHumanHint[] = [], status?: SongHumanHintsStatus | null): { items: HumanHint[]; status: HumanHintsStatus } {
	const items = rows
		.filter((row) => Boolean(row?.id))
		.map((row) => ({
			id: String(row.id),
			startTime: toNumber(row.start_time),
			endTime: Math.max(toNumber(row.start_time), toNumber(row.end_time, toNumber(row.start_time))),
			title: String(row.title ?? "").trim(),
			summary: String(row.summary ?? "").trim(),
			lightingHint: String(row.lighting_hint ?? "").trim(),
		}))
		.sort((left, right) => left.startTime - right.startTime || left.endTime - right.endTime || left.id.localeCompare(right.id));
	return {
		items,
		status: {
			dirty: status?.dirty === true,
			saved: status?.saved !== false,
			fileExists: status?.file_exists === true,
		},
	};
}