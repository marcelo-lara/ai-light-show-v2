import { Card } from "../../../shared/components/layout/Card.ts";
import { getBackendStore } from "../../../shared/state/backend_state.ts";
import { transportJumpToSection } from "../../../shared/transport/transport_intents.ts";
import type { SongSection } from "../../../shared/transport/protocol.ts";

function formatSectionStart(startSeconds: number): string {
  const safeValue = Number.isFinite(startSeconds) ? startSeconds : 0;
  return safeValue.toFixed(2);
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
  const store = getBackendStore();
  const content = document.createElement("div");
  content.className = "show-control-body";

  const list = document.createElement("ol");
  list.className = "show-control-list mono";

  const sections = normalizedSections(store.state.song?.sections);
  const highlightedIndex = activeSectionIndex(sections, store.state.playback?.time_ms);
  for (const [index, section] of sections.entries()) {
    const item = document.createElement("li");
    const isActive = index === highlightedIndex;
    item.className = `show-control-row${isActive ? " is-active" : ""}`;
    item.tabIndex = 0;
    item.setAttribute("role", "button");
    item.onclick = () => transportJumpToSection(index);
    item.onkeydown = (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      transportJumpToSection(index);
    };

    const time = document.createElement("span");
    time.className = "show-control-time";
    time.textContent = formatSectionStart(section.start_s);

    const name = document.createElement("span");
    name.className = "show-control-label";
    name.textContent = section.name;

    item.append(time, name);
    list.appendChild(item);
  }

  if (sections.length === 0) {
    const item = document.createElement("li");
    item.className = "show-control-row is-active";

    const time = document.createElement("span");
    time.className = "show-control-time";
    time.textContent = "--.--";

    const name = document.createElement("span");
    name.className = "show-control-label";
    name.textContent = "No sections available";

    item.append(time, name);
    list.appendChild(item);
  }

  content.appendChild(list);
  return Card(content, { variant: "outlined", className: "show-control-panel" });
}