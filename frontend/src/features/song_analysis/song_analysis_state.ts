import { getBackendStore } from "../../shared/state/backend_state.ts";
import { getSongStructureData } from "../../shared/state/song_data.ts";
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

export function getSongAnalysisData(): SongAnalysisData {
  const song = getBackendStore().state.song;
  if (!song) return { beats: [], chords: [], sections: [], plots: [] };

  const beats = cleanBeatObjects(song.beats);

  const plots = (song.analysis?.plots ?? [])
    .filter((plot) => Boolean(plot?.id) && Boolean(plot?.title) && Boolean(plot?.svg_url))
    .map((plot) => ({
      id: String(plot!.id),
      title: String(plot!.title),
      svgUrl: resolveBackendUrl(String(plot!.svg_url)),
    }));

  return {
    beats,
    ...getSongStructureData(),
    plots,
  };
}
