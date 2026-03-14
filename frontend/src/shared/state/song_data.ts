import { getBackendStore } from "./backend_state.ts";
import type { BeatObject, SongSection, SongState } from "../transport/protocol.ts";

export type SongStructureData = {
	beats: BeatObject[];
	sections: SongSection[];
};

function cleanBeats(song: SongState): BeatObject[] {
	const rows = song.beats;
	if (!Array.isArray(rows)) return [];
	console.debug("[CHORD_DEBUG] cleanBeats input", rows.slice(0, 8));

	const picked: BeatObject[] = [];
	for (const row of rows) {
		if (!row || typeof row !== "object") continue;
		const time = Number((row as BeatObject).time);
		const bar = Number((row as BeatObject).bar);
		const beat = Number((row as BeatObject).beat);
		if (!Number.isFinite(time) || !Number.isFinite(bar) || !Number.isFinite(beat)) continue;
		picked.push({
			time,
			bar,
			beat,
			bass: (row as BeatObject).bass ? String((row as BeatObject).bass) : undefined,
			chord: (row as BeatObject).chord ? String((row as BeatObject).chord) : undefined,
		});
	}

	picked.sort((a, b) => a.time - b.time);
	console.debug("[CHORD_DEBUG] cleanBeats output", picked.slice(0, 8));
	return picked;
}

function cleanSections(song: SongState): SongSection[] {
	const rows = song.sections;
	if (!Array.isArray(rows)) return [];
	console.debug("[CHORD_DEBUG] cleanSections input", rows.slice(0, 6));

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
	console.debug("[CHORD_DEBUG] cleanSections output", picked.slice(0, 6));
	return picked;
}

export function getSongStructureData(): SongStructureData {
	const song = getBackendStore().state.song;
	if (!song) return { beats: [], sections: [] };
	const result = {
		beats: cleanBeats(song),
		sections: cleanSections(song),
	};
	console.debug("[CHORD_DEBUG] getSongStructureData", {
		song: song.filename,
		beats: result.beats.slice(0, 8),
		sections: result.sections.slice(0, 6),
	});
	return result;
}