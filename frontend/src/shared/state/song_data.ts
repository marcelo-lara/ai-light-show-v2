import { getBackendStore } from "./backend_state.ts";
import type { SongChord, SongSection, SongState } from "../transport/protocol.ts";

export type SongStructureData = {
	chords: SongChord[];
	sections: SongSection[];
};

function cleanChords(song: SongState): SongChord[] {
	const rows = song.analysis?.chords;
	if (!Array.isArray(rows)) return [];

	const picked: SongChord[] = [];
	for (const row of rows) {
		if (!row || typeof row !== "object") continue;
		const time = Number((row as SongChord).time_s);
		const label = String((row as SongChord).label ?? "").trim();
		if (!Number.isFinite(time) || !label) continue;
		picked.push({
			time_s: time,
			label,
			bar: Number.isFinite(Number((row as SongChord).bar)) ? Number((row as SongChord).bar) : undefined,
			beat: Number.isFinite(Number((row as SongChord).beat)) ? Number((row as SongChord).beat) : undefined,
		});
	}

	picked.sort((a, b) => a.time_s - b.time_s);
	return picked;
}

function cleanSections(song: SongState): SongSection[] {
	const rows = song.sections;
	if (!Array.isArray(rows)) return [];

	const picked: SongSection[] = [];
	for (const row of rows) {
		if (!row || typeof row !== "object") continue;
		const start = Number((row as SongSection).start_s);
		const end = Number((row as SongSection).end_s);
		const name = String((row as SongSection).name ?? "").trim();
		if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start || !name) continue;
		picked.push({ name, start_s: start, end_s: end });
	}

	picked.sort((a, b) => a.start_s - b.start_s);
	return picked;
}

export function getSongStructureData(): SongStructureData {
	const song = getBackendStore().state.song;
	if (!song) return { chords: [], sections: [] };
	return {
		chords: cleanChords(song),
		sections: cleanSections(song),
	};
}