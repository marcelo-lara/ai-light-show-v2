import { getBackendStore } from "../../shared/state/backend_state.ts";
import type { SongChord, SongState } from "../../shared/transport/protocol.ts";

type BackendOriginGlobal = typeof globalThis & {
  __BACKEND_HTTP_ORIGIN__?: string;
};

export type SongAnalysisData = {
  beats: number[];
  downbeats: number[];
  chords: SongChord[];
  plots: Array<{ id: string; title: string; svgUrl: string }>;
};

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

export function getSongAnalysisData(): SongAnalysisData {
  const song = getBackendStore().state.song;
  if (!song) return { beats: [], downbeats: [], chords: [], plots: [] };

  const plots = (song.analysis?.plots ?? [])
    .filter((plot) => Boolean(plot?.id) && Boolean(plot?.title) && Boolean(plot?.svg_url))
    .map((plot) => ({
      id: String(plot!.id),
      title: String(plot!.title),
      svgUrl: resolveBackendUrl(String(plot!.svg_url)),
    }));

  return {
    beats: cleanSortedNumeric(song.beats),
    downbeats: cleanSortedNumeric(song.downbeats),
    chords: cleanChords(song),
    plots,
  };
}
