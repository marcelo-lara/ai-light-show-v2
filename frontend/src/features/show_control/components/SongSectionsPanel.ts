import { Card } from "../../../shared/components/layout/Card.ts";
import { List } from "../../../shared/components/layout/List.ts";
import { getBackendStore, subscribeBackendStore } from "../../../shared/state/backend_state.ts";
import { transportJumpToSection } from "../../../shared/transport/transport_intents.ts";
import type { SongSection } from "../../../shared/transport/protocol.ts";

function formatSectionStart(startSeconds: number): string {
  const safeValue = Number.isFinite(startSeconds) ? startSeconds : 0;
  return safeValue.toFixed(3);
}

function normalizedSections(sections: SongSection[] | undefined): SongSection[] {
  if (!sections || sections.length === 0) return [];
  return [...sections].sort((a, b) => a.start_s - b.start_s);
}

function activeSectionIndex(sections: SongSection[], timeMs: number | undefined): number {
  if (sections.length === 0) return -1;
  if (typeof timeMs !== "number" || !Number.isFinite(timeMs)) return -1;

  const timeS = Math.max(0, timeMs / 1000);
  for (let index = 0; index < sections.length; index++) {
    const start = Number(sections[index]?.start_s ?? 0) - 0.01; // Add a small tolerance to ensure the section becomes active just before its start time
    const end = Number(sections[index]?.end_s ?? 0);
    if (timeS > start && timeS < end) return index;
  }

  return -1;
}

export function SongSectionsPanel(): HTMLElement {
  const content = document.createElement("div");
  content.className = "show-control-body";

  const list = document.createElement("div");
  list.className = "show-control-list o-list";
  content.appendChild(list);

  const render = () => {
    const state = getBackendStore().state;
    const sections = normalizedSections(state.song?.sections);
    const highlightedIndex = activeSectionIndex(sections, state.playback?.time_ms);
    list.replaceChildren();

    for (const [index, section] of sections.entries()) {
      const isActive = index === highlightedIndex;

      const time = document.createElement("span");
      time.className = "show-control-time u-cell u-cell-time";
      time.textContent = formatSectionStart(section.start_s);

      const name = document.createElement("span");
      name.className = "show-control-label u-cell u-cell-effect";
      name.textContent = section.name;

      const item = List({
        className: "show-control-row",
        content: [time, name],
        isActive,
      });
      item.tabIndex = 0;
      item.setAttribute("role", "button");
      item.onclick = () => transportJumpToSection(index);
      item.onkeydown = (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        transportJumpToSection(index);
      };

      list.appendChild(item);
    }

    if (sections.length > 0) return;

    const time = document.createElement("span");
    time.className = "show-control-time u-cell u-cell-time";
    time.textContent = "--.--";

    const name = document.createElement("span");
    name.className = "show-control-label u-cell u-cell-effect";
    name.textContent = "No sections available";

    const item = List({
      className: "show-control-row",
      content: [time, name],
      isActive: true,
    });
    list.appendChild(item);
  };

  render();
  const card = Card(content, { variant: "outlined", className: "show-control-panel" });
  (card as unknown as { _cleanup: () => void })._cleanup = subscribeBackendStore(render);
  return card;
}