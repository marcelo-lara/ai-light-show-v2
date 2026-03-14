import { getBackendStore } from "../../shared/state/backend_state.ts";
import { getSongStructureData } from "../../shared/state/song_data.ts";
import type { SongSection, BeatObject } from "../../shared/transport/protocol.ts";

type BackendOriginGlobal = typeof globalThis & {
  __BACKEND_HTTP_ORIGIN__?: string;
};

export type SongAnalysisData = {
  beats: BeatObject[];
  sections: SongSection[];
  plots: Array<{ id: string; title: string; svgUrl: string }>;
};

function resolveBackendUrl(rawUrl: string): string {
  if (rawUrl.startsWith("http://") || rawUrl.startsWith("https://")) return rawUrl;
  const origin = String((globalThis as BackendOriginGlobal).__BACKEND_HTTP_ORIGIN__ ?? "").trim();
  if (rawUrl.startsWith("/") && origin) return `${origin}${rawUrl}`;
  return rawUrl;
}

export function getSongAnalysisData(): SongAnalysisData {
  const song = getBackendStore().state.song;
  if (!song) return { beats: [], sections: [], plots: [] };

  const plots = (song.analysis?.plots ?? [])
    .filter((plot) => Boolean(plot?.id) && Boolean(plot?.title) && Boolean(plot?.svg_url))
    .map((plot) => ({
      id: String(plot!.id),
      title: String(plot!.title),
      svgUrl: resolveBackendUrl(String(plot!.svg_url)),
    }));

  return {
    ...getSongStructureData(),
    plots,
  };
}
