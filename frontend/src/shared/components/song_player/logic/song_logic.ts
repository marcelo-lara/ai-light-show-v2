import type { SongState, BeatObject } from "../../../transport/protocol.ts";
import type { Section } from "../types/types.ts";

export function cleanSortedNumeric(values: unknown): number[] {
  if (!Array.isArray(values)) return [];
  return values
    .map((value) => Number(value))
    .filter((value) => Number.isFinite(value) && value >= 0)
    .sort((a, b) => a - b);
}

export function cleanBeatObjects(values: unknown): BeatObject[] {
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

export function normalizeSections(input: unknown): Section[] {
  const parts = Array.isArray(input) ? input : [];
  return parts
    .map((section: any) => ({
      name: String(section?.name ?? "Section"),
      start_s: Number(section?.start_s ?? 0),
      end_s: Number(section?.end_s ?? 0),
    }))
    .filter((section) => Number.isFinite(section.start_s) && Number.isFinite(section.end_s) && section.end_s > section.start_s)
    .sort((a, b) => a.start_s - b.start_s);
}

export function findCurrentSectionIndex(sections: Section[], tSeconds: number): number | null {
  for (let idx = 0; idx < sections.length; idx++) {
    const section = sections[idx];
    if (section.start_s <= tSeconds && tSeconds < section.end_s) {
      return idx;
    }
  }
  return null;
}

export function getPrevBeatTimeMs(beats: number[], currentTimeMs: number): number {
  const t = currentTimeMs / 1000;
  let target = 0;
  for (const beat of beats) {
    if (beat >= t - 0.01) break;
    target = beat;
  }
  return Math.round(target * 1000);
}

export function getNextBeatTimeMs(beats: number[], currentTimeMs: number): number {
  const t = currentTimeMs / 1000;
  const lastBeat = beats[beats.length - 1] ?? 0;
  let target = lastBeat;
  for (const beat of beats) {
    if (beat > t + 0.01) {
      target = beat;
      break;
    }
  }
  return Math.round(target * 1000);
}

export function getPrevSectionTargetIndex(sections: Section[], currentTimeMs: number): number {
  const t = currentTimeMs / 1000;
  const current = findCurrentSectionIndex(sections, t);

  if (current === null) {
    let before = -1;
    for (let idx = 0; idx < sections.length; idx++) {
      if (sections[idx].start_s < t - 0.01) before = idx;
    }
    return before;
  }

  return current - 1;
}

export function getNextSectionTargetIndex(sections: Section[], currentTimeMs: number): number {
  const t = currentTimeMs / 1000;
  const current = findCurrentSectionIndex(sections, t);

  let targetIndex = sections.length - 1;
  if (current === null) {
    for (let idx = 0; idx < sections.length; idx++) {
      if (sections[idx].start_s > t + 0.01) {
        targetIndex = idx;
        break;
      }
    }
  } else if (current < sections.length - 1) {
    targetIndex = current + 1;
  }

  return targetIndex;
}

export function getImplicitLoopSectionIndex(sections: Section[], currentTimeMs: number): number | null {
  const t = currentTimeMs / 1000;
  for (let idx = 0; idx < sections.length; idx++) {
    if (sections[idx].start_s > t + 0.001) {
      return idx;
    }
  }
  return null;
}

export function computeBarBeatLabel(downbeats: number[], beats: number[], timeMs: number): string {
  if (!downbeats.length) return "1.1";

  const t = timeMs / 1000;
  let barIndex = 0;
  for (let idx = 0; idx < downbeats.length; idx++) {
    if (downbeats[idx] <= t) barIndex = idx;
    else break;
  }

  const barStart = downbeats[barIndex] ?? 0;
  let beatIndex = 1;
  for (const beat of beats) {
    if (beat > barStart && beat <= t + 0.0005) {
      beatIndex += 1;
    }
    if (beat > t) break;
  }

  return `${barIndex + 1}.${Math.min(9, Math.max(1, beatIndex))}`;
}

export function songFingerprint(song: SongState): string {
  const sections = Array.isArray(song.sections) ? song.sections : [];
  const beatObjects = cleanBeatObjects(song.beats);
  const beats = beatObjects.map(b => b.time);
  const downbeats = beatObjects.filter(b => b.beat === 1).map(b => b.time);

  const firstSection = sections[0] as any;
  const lastSection = sections[sections.length - 1] as any;
  const lastBeat = beats.length > 0 ? beats[beats.length - 1] : "";
  const lastDownbeat = downbeats.length > 0 ? downbeats[downbeats.length - 1] : "";

  return [
    song.filename ?? "",
    song.audio_url ?? "",
    song.length_s ?? "",
    song.bpm ?? "",
    sections.length,
    firstSection ? `${firstSection.start_s}:${firstSection.end_s}:${firstSection.name}` : "",
    lastSection ? `${lastSection.start_s}:${lastSection.end_s}:${lastSection.name}` : "",
    beats.length,
    lastBeat,
    downbeats.length,
    lastDownbeat,
  ].join("|");
}
