import type { SongChord, SongSection } from "../../../../shared/transport/protocol.ts";

export type ChordsPanelProps = {
  chords: SongChord[];
  sections: SongSection[];
};

export type ChordSectionGroup = {
  label: string;
  start_s: number;
  end_s: number;
  chords: SongChord[];
};
