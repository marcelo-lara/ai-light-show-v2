import type { SongAnalysisEvent, SongState } from "../../../transport/protocol.ts";
import type { SongPlayerEvent } from "../types/types.ts";

function toFiniteNumber(value: unknown): number {
  const picked = Number(value);
  return Number.isFinite(picked) ? picked : 0;
}

function normalizeEvent(row: SongAnalysisEvent): SongPlayerEvent | null {
  const id = String(row.id ?? "").trim();
  const type = String(row.type ?? "").trim();
  const start_s = toFiniteNumber(row.start_time);
  const end_s = toFiniteNumber(row.end_time);
  if (!id || !type || end_s <= start_s) return null;
  return {
    id,
    type,
    start_s,
    end_s,
    intensity: toFiniteNumber(row.intensity),
  };
}

export function normalizeSongEvents(song: SongState): SongPlayerEvent[] {
  const items = (song.analysis?.events ?? [])
    .map(normalizeEvent)
    .filter((event): event is SongPlayerEvent => event !== null);
  items.sort((left, right) => left.start_s - right.start_s || left.end_s - right.end_s || left.id.localeCompare(right.id));
  return items;
}

export function activeSongEvents(events: SongPlayerEvent[], timeMs: number): SongPlayerEvent[] {
  if (!Number.isFinite(timeMs)) return [];
  const cursor_s = Math.max(0, timeMs / 1000);
  return events.filter((event) => cursor_s >= event.start_s && cursor_s < event.end_s);
}

export function activeSongEventKey(events: SongPlayerEvent[], timeMs: number): string {
  return activeSongEvents(events, timeMs).map((event) => event.id).join("|");
}