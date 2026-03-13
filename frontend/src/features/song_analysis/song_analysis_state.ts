import { getBackendStore } from "../../shared/state/backend_state.ts";
import type { SongChord, SongSection, SongState, BeatObject } from "../../shared/transport/protocol.ts";

type BackendOriginGlobal = typeof globalThis & {
  __BACKEND_HTTP_ORIGIN__?: string;
};

export type SongAnalysisData = {
  beats: BeatObject[];
  chords: SongChord[];
  sections: SongSection[];
  plots: Array<{ id: string; title: string; svgUrl: string }>;
};

const MOCK_BEATS: BeatObject[] = [
  { time: 1.376, bar: 0, beat: 1 },
  { time: 1.824, bar: 0, beat: 2 },
  { time: 2.272, bar: 0, beat: 3 },
  { time: 2.709, bar: 0, beat: 4 },
  { time: 3.168, bar: 1, beat: 1 },
  { time: 3.605, bar: 1, beat: 2 },
  { time: 4.064, bar: 1, beat: 3 },
  { time: 4.501, bar: 1, beat: 4 },
  { time: 4.96, bar: 2, beat: 1 },
  { time: 5.397, bar: 2, beat: 2 },
  { time: 5.856, bar: 2, beat: 3 },
  { time: 6.293, bar: 2, beat: 4 },
  { time: 6.731, bar: 3, beat: 1 },
  { time: 7.179, bar: 3, beat: 2 },
  { time: 7.637, bar: 3, beat: 3 },
  { time: 8.064, bar: 3, beat: 4 },
];

function resolveBackendUrl(rawUrl: string): string {
  if (rawUrl.startsWith("http://") || rawUrl.startsWith("https://")) return rawUrl;
  const origin = String((globalThis as BackendOriginGlobal).__BACKEND_HTTP_ORIGIN__ ?? "").trim();
  if (rawUrl.startsWith("/") && origin) return `${origin}${rawUrl}`;
  return rawUrl;
}

function cleanBeatObjects(values: unknown): BeatObject[] {
  if (!Array.isArray(values)) return [];
  const picked: BeatObject[] = [];
  for (const value of values) {
    if (!value || typeof value !== "object") continue;
    const obj = value as Partial<BeatObject>;
    const time = Number(obj.time);
    const bar = Number(obj.bar);
    const beat = Number(obj.beat);
    if (!Number.isFinite(time) || !Number.isFinite(bar) || !Number.isFinite(beat)) continue;
    picked.push({
      time,
      bar,
      beat,
      bass: obj.bass ? String(obj.bass) : undefined,
      chord: obj.chord ? String(obj.chord) : undefined,
    });
  }
  picked.sort((a, b) => a.time - b.time);
  return picked;
}

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

export function getSongAnalysisData(): SongAnalysisData {
  const song = getBackendStore().state.song;
  if (!song) return { beats: [], chords: [], sections: [], plots: [] };

  const beats = cleanBeatObjects(song.beats);
  const fallbackBeats = beats.length ? beats : MOCK_BEATS;

  const plots = (song.analysis?.plots ?? [])
    .filter((plot) => Boolean(plot?.id) && Boolean(plot?.title) && Boolean(plot?.svg_url))
    .map((plot) => ({
      id: String(plot!.id),
      title: String(plot!.title),
      svgUrl: resolveBackendUrl(String(plot!.svg_url)),
    }));

  return {
    beats: fallbackBeats,
    chords: cleanChords(song),
    sections: cleanSections(song),
    plots,
  };
}
