import type { SongChord, SongSection } from "../../transport/protocol.ts";
import type { ChordSectionGroup } from "./types.ts";

const CHORD_SECTION_SIZE = 8;

export function groupChordsBySections(chords: SongChord[], sections: SongSection[]): ChordSectionGroup[] {
	if (sections.length) {
		const groups: ChordSectionGroup[] = [];
		for (const section of sections) {
			const sectionChords = chords.filter((chord) => chord.time_s > section.start_s && chord.time_s < section.end_s);
			if (!sectionChords.length) continue;
			groups.push({
				label: section.name,
				start_s: section.start_s,
				end_s: section.end_s,
				chords: sectionChords,
			});
		}
		return groups;
	}

	const groups: ChordSectionGroup[] = [];
	for (let offset = 0; offset < chords.length; offset += CHORD_SECTION_SIZE) {
		const chunk = chords.slice(offset, offset + CHORD_SECTION_SIZE);
		if (!chunk.length) continue;
		const first = chunk[0]?.time_s ?? 0;
		const last = chunk[chunk.length - 1]?.time_s ?? first;
		groups.push({
			label: `Section ${groups.length + 1}`,
			start_s: first,
			end_s: last,
			chords: chunk,
		});
	}
	return groups;
}