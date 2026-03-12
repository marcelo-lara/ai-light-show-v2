import { getBackendStore } from "../../shared/state/backend_state.ts";
import type { SongChord, SongSection, SongState } from "../../shared/transport/protocol.ts";

type BackendOriginGlobal = typeof globalThis & {
  __BACKEND_HTTP_ORIGIN__?: string;
};

export type SongAnalysisData = {
  beats: number[];
  downbeats: number[];
  chords: SongChord[];
  sections: SongSection[];
  plots: Array<{ id: string; title: string; svgUrl: string }>;
};

const MOCK_BEATS = [
  1.376, 1.824, 2.272, 2.709, 3.168, 3.605, 4.064, 4.501,
  4.96, 5.397, 5.856, 6.293, 6.731, 7.179, 7.637, 8.064,
  8.48, 8.971, 9.44, 9.888, 10.357, 10.795, 11.253, 11.712,
  12.139, 12.597, 13.024, 13.461, 13.909, 14.357, 14.795, 15.2,
];

const MOCK_DOWNBEATS = [1.824, 3.605, 5.397, 7.179, 8.971, 10.795, 12.597, 14.357];

function resolveBackendUrl(rawUrl: string): string {
  if (rawUrl.startsWith("http://") || rawUrl.startsWith("https://")) return rawUrl;
  const origin = String((globalThis as BackendOriginGlobal).__BACKEND_HTTP_ORIGIN__ ?? "").trim();
  if (rawUrl.startsWith("/") && origin) return `${origin}${rawUrl}`;
  return rawUrl;
}

function cleanSortedNumeric(values: unknown): number[] {
  if (!Array.isArray(values)) return [];
  const picked: number[] = [];
  for (const value of values) {
    const num = Number(value);
    if (Number.isFinite(num)) picked.push(num);
  }
  picked.sort((a, b) => a - b);
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
  if (!song) return { beats: [], downbeats: [], chords: [], sections: [], plots: [] };

  const beats = cleanSortedNumeric(song.beats);
  const downbeats = cleanSortedNumeric(song.downbeats);
  const fallbackBeats = beats.length ? beats : MOCK_BEATS;
  const fallbackDownbeats = downbeats.length ? downbeats : MOCK_DOWNBEATS;

  const plots = (song.analysis?.plots ?? [])
    .filter((plot) => Boolean(plot?.id) && Boolean(plot?.title) && Boolean(plot?.svg_url))
    .map((plot) => ({
      id: String(plot!.id),
      title: String(plot!.title),
      svgUrl: resolveBackendUrl(String(plot!.svg_url)),
    }));

  return {
    beats: fallbackBeats,
    downbeats: fallbackDownbeats,
    chords: cleanChords(song),
    sections: cleanSections(song),
    plots,
  };
}
