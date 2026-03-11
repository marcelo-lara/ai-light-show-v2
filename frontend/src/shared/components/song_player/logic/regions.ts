import type { Section } from "../types/types.ts";

type RebuildRegionsArgs = {
  regionsPlugin: any;
  sections: Section[];
  downbeats: number[];
  showSections: boolean;
  showDownbeats: boolean;
  selectedSectionIndex: number | null;
  onSelectSection: (index: number) => void;
};

export function rebuildSongRegions(args: RebuildRegionsArgs) {
  const {
    regionsPlugin,
    sections,
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
