import type { Section } from "../types/types.ts";
import {
  getImplicitLoopSectionIndex,
  getNextBeatTimeMs,
  getNextSectionTargetIndex,
  getPrevBeatTimeMs,
  getPrevSectionTargetIndex,
} from "./song_logic.ts";

export function previousBeatTargetMs(beats: number[], localTimeMs: number): number {
  return getPrevBeatTimeMs(beats, localTimeMs);
}

export function nextBeatTargetMs(beats: number[], localTimeMs: number): number {
  return getNextBeatTimeMs(beats, localTimeMs);
}

export type SectionJump = {
  selectedSectionIndex: number | null;
  targetMs: number;
};

export function previousSectionJump(sections: Section[], localTimeMs: number): SectionJump | null {
  if (sections.length === 0) return null;
  const targetIndex = getPrevSectionTargetIndex(sections, localTimeMs);
  if (targetIndex < 0) {
    return { selectedSectionIndex: null, targetMs: 0 };
  }
  return {
    selectedSectionIndex: targetIndex,
    targetMs: Math.round(sections[targetIndex].start_s * 1000),
  };
}

export function nextSectionJump(sections: Section[], localTimeMs: number): SectionJump | null {
  if (sections.length === 0) return null;
  const targetIndex = getNextSectionTargetIndex(sections, localTimeMs);
  return {
    selectedSectionIndex: targetIndex,
    targetMs: Math.round(sections[targetIndex].start_s * 1000),
  };
}

export function implicitLoopIndex(
  sections: Section[],
  loopEnabled: boolean,
  selectedSectionIndex: number | null,
  localTimeMs: number,
): number | null {
  if (!loopEnabled || selectedSectionIndex !== null) return null;
  return getImplicitLoopSectionIndex(sections, localTimeMs);
}

export function loopWrapTargetMs(params: {
  sections: Section[];
  loopEnabled: boolean;
  selectedSectionIndex: number | null;
  implicitLoopSectionIndex: number | null;
  localTimeMs: number;
}): number | null {
  const { sections, loopEnabled, selectedSectionIndex, implicitLoopSectionIndex, localTimeMs } = params;
  if (!loopEnabled || sections.length === 0) return null;
  if (selectedSectionIndex === null && implicitLoopSectionIndex === null) return null;

  const targetIndex = selectedSectionIndex ?? implicitLoopSectionIndex;
  if (targetIndex === null) return null;
  const section = sections[targetIndex];
  if (!section) return null;

  const t = localTimeMs / 1000;
  if (selectedSectionIndex === null && t < section.start_s) return null;
  return t >= (section.end_s - 0.012) ? Math.round(section.start_s * 1000) : null;
}
