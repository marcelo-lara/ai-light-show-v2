import type { Section } from "../types/types.ts";
import type { SongPlayerEvent } from "../types/types.ts";

type RebuildRegionsArgs = {
  regionsPlugin: any;
  sections: Section[];
  activeEvents: SongPlayerEvent[];
  downbeats: number[];
  showSections: boolean;
  showDownbeats: boolean;
  selectedSectionIndex: number | null;
  onSelectSection: (index: number) => void;
};

function activeEventColor(event: SongPlayerEvent): string {
  const intensity = Math.max(0, Math.min(event.intensity, 1));
  const weight = Math.round(28 + intensity * 30);
  return `color-mix(in oklab, var(--accent-2) ${weight}%, transparent)`;
}

export function rebuildSongRegions(args: RebuildRegionsArgs) {
  const {
    regionsPlugin,
    sections,
    activeEvents,
    downbeats,
    showSections,
    showDownbeats,
    selectedSectionIndex,
    onSelectSection,
  } = args;

  if (!regionsPlugin) return;

  regionsPlugin.clearRegions();

  if (showSections) {
    for (let idx = 0; idx < sections.length; idx++) {
      const section = sections[idx];
      const selected = idx === selectedSectionIndex;
      const region = regionsPlugin.addRegion({
        start: section.start_s,
        end: section.end_s,
        content: section.name,
        color: selected
          ? "color-mix(in oklab, var(--accent-2) 35%, transparent)"
          : "color-mix(in oklab, var(--accent) 25%, transparent)",
        drag: false,
        resize: false,
      });

      region.on?.("click", (event: Event) => {
        event.preventDefault();
        event.stopPropagation();
        onSelectSection(idx);
      });
    }
  }

  for (const event of activeEvents) {
    const region = regionsPlugin.addRegion({
      start: event.start_s,
      end: event.end_s,
      color: activeEventColor(event),
      drag: false,
      resize: false,
    });

    region.element?.classList.add("song-player-region-event");
    if (region.element) {
      region.element.dataset.eventType = event.type;
      region.element.style.pointerEvents = "none";
    }
  }

  if (showDownbeats) {
    for (const downbeat of downbeats) {
      regionsPlugin.addRegion({
        start: downbeat,
        end: downbeat + 0.015,
        color: "color-mix(in oklab, var(--text) 45%, transparent)",
        drag: false,
        resize: false,
      });
    }
  }
}
