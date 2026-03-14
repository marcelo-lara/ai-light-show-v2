import type { BeatObject, SongSection } from "../../transport/protocol.ts";
import type { BeatSectionGroup } from "./types.ts";

const UNASSIGNED_LABEL = "unassigned";

function byTime<T extends { time?: number; start_s?: number }>(left: T, right: T): number {
	const leftTime = left.time ?? left.start_s ?? 0;
	const rightTime = right.time ?? right.start_s ?? 0;
	return leftTime - rightTime;
}

function buildGroup(label: string, beats: BeatObject[]): BeatSectionGroup | null {
	if (!beats.length) return null;
	const ordered = [...beats].sort(byTime);
	return {
		label,
		start_s: ordered[0]?.time ?? 0,
		end_s: ordered[ordered.length - 1]?.time ?? 0,
		beats: ordered,
	};
}

function isBeatInSection(beat: BeatObject, section: SongSection): boolean {
	return beat.time >= section.start_s && beat.time < section.end_s;
}

export function groupBeatsBySections(beats: BeatObject[], sections: SongSection[]): BeatSectionGroup[] {
	console.debug("[CHORD_DEBUG] groupBeatsBySections input", {
		beats: beats.slice(0, 8),
		sections: sections.slice(0, 6),
	});
	if (sections.length) {
		const orderedBeats = [...beats].sort(byTime);
		const orderedSections = [...sections].sort(byTime);
		const groups: BeatSectionGroup[] = [];
		let beatIndex = 0;

		for (const section of orderedSections) {
			const unassignedBeats: BeatObject[] = [];
			while (beatIndex < orderedBeats.length && orderedBeats[beatIndex].time < section.start_s) {
				unassignedBeats.push(orderedBeats[beatIndex]);
				beatIndex += 1;
			}

			const unassignedGroup = buildGroup(UNASSIGNED_LABEL, unassignedBeats);
			if (unassignedGroup) {
				groups.push(unassignedGroup);
			}

			const sectionBeats: BeatObject[] = [];
			while (beatIndex < orderedBeats.length && isBeatInSection(orderedBeats[beatIndex], section)) {
				sectionBeats.push(orderedBeats[beatIndex]);
				beatIndex += 1;
			}

			console.debug("[CHORD_DEBUG] section filter", {
				section,
				sectionBeats: sectionBeats.slice(0, 8),
				leadingUnassigned: unassignedBeats.slice(0, 8),
			});

			const sectionGroup = buildGroup(section.name, sectionBeats);
			if (sectionGroup) {
				groups.push({
					...sectionGroup,
					start_s: section.start_s,
					end_s: section.end_s,
				});
			}
		}

		const trailingUnassigned = buildGroup(UNASSIGNED_LABEL, orderedBeats.slice(beatIndex));
		if (trailingUnassigned) {
			groups.push(trailingUnassigned);
		}
		console.debug("[CHORD_DEBUG] grouped sections output", groups.slice(0, 6));
		return groups;
	}

	const groups = buildGroup(UNASSIGNED_LABEL, beats) ? [buildGroup(UNASSIGNED_LABEL, beats)!] : [];
	console.debug("[CHORD_DEBUG] grouped fallback output", groups.slice(0, 6));
	return groups;
}