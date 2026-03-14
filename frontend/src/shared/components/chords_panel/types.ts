import type { SongChord, SongSection } from "../../transport/protocol.ts";

export type ChordsPanelProps = {
	chords: SongChord[];
	sections: SongSection[];
	cardClassName?: string;
};

export type ChordSectionGroup = {
	label: string;
	start_s: number;
	end_s: number;
	chords: SongChord[];
};