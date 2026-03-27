import type { SongState, BeatObject } from "../../../transport/protocol.ts";
import type { Section } from "../types/types.ts";
import { cleanBeatObjects, normalizeSections, songFingerprint } from "./song_logic.ts";

type BackendOriginGlobal = typeof globalThis & {
  __BACKEND_HTTP_ORIGIN__?: string;
};

export type SongIdentity = {
  key: string;
  fingerprint: string;
};

export type DerivedSongData = {
  label: string;
  beatObjects: BeatObject[];
  sections: Section[];
  beats: number[];
  downbeats: number[];
  durationMs: number;
  selectedSectionIndex: number | null;
  implicitLoopSectionIndex: number | null;
};

export function songIdentity(song: SongState): SongIdentity {
  return {
    key: `${song.filename ?? ""}|${song.audio_url ?? ""}`,
    fingerprint: songFingerprint(song),
  };
}

export function deriveSongData(
  song: SongState,
  currentDurationMs: number,
  selectedSectionIndex: number | null,
  implicitLoopSectionIndex: number | null,
): DerivedSongData {
  const sections = normalizeSections(song.sections);
  const beatObjects = cleanBeatObjects(song.beats);
  const beats = beatObjects.map(b => b.time);
  const downbeats = beatObjects.filter(b => b.beat === 1).map(b => b.time);
  const songLengthMs = Number(song.length_s ?? 0) * 1000;
  const durationMs = Number.isFinite(songLengthMs) && songLengthMs > 0
    ? Math.max(currentDurationMs, Math.round(songLengthMs))
    : currentDurationMs;

  return {
    label: song.filename ? `Song: ${song.filename}` : "Song loaded",
    beatObjects,
    sections,
    beats,
    downbeats,
    durationMs,
    selectedSectionIndex: selectedSectionIndex !== null && selectedSectionIndex >= sections.length
      ? null
      : selectedSectionIndex,
    implicitLoopSectionIndex:
      implicitLoopSectionIndex !== null && implicitLoopSectionIndex >= sections.length
        ? null
        : implicitLoopSectionIndex,
  };
}

export function pausedPlaybackTimeMs(rawTimeMs: unknown): number {
  const timeMs = Number(rawTimeMs ?? 0);
  return Number.isFinite(timeMs) ? Math.max(0, timeMs) : 0;
}

export function shouldAdjustWaveTime(currentSeconds: number, targetMs: number): boolean {
  return Math.abs(currentSeconds - (targetMs / 1000)) > 0.02;
}

export function resolveSongAudioUrl(rawUrl: string | null): string | null {
  if (!rawUrl) return null;
  if (rawUrl.startsWith("http://") || rawUrl.startsWith("https://")) return rawUrl;
  const origin = String((globalThis as BackendOriginGlobal).__BACKEND_HTTP_ORIGIN__ ?? "").trim();
  if (rawUrl.startsWith("/") && origin) return `${origin}${rawUrl}`;
  return rawUrl;
}
