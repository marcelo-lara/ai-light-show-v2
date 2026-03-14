import type { BeatObject, SongSection } from "../../transport/protocol.ts";

export type ChordsPanelProps = {
	beats: BeatObject[];
	sections: SongSection[];
	cardClassName?: string;
};

export type BeatSectionGroup = {
	label: string;
	start_s: number;
	end_s: number;
	beats: BeatObject[];
};