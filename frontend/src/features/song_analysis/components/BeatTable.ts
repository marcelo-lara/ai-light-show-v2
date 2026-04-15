import { Card } from "../../../shared/components/layout/Card.ts";
import type { BeatObject } from "../../../shared/transport/protocol.ts";
import { formatPosition } from "../../../shared/utils/format.ts";

type BeatTableProps = {
  beats: BeatObject[];
};

type BeatGroup = {
  label: string;
  beats: BeatObject[];
};

const BEAT_GROUP_PAGE_SIZE = 4;

function groupBeats(beats: BeatObject[]): BeatGroup[] {
  if (!beats.length) return [];

  const groups: BeatGroup[] = [];
  let currentBar = beats[0].bar;
  let currentGroup: BeatObject[] = [];

  for (const beat of beats) {
    if (beat.bar !== currentBar) {
      if (currentGroup.length) {
        groups.push({ label: `Bar ${currentBar}`, beats: currentGroup });
      }
      currentBar = beat.bar;
      currentGroup = [];
    }
    currentGroup.push(beat);
  }

  if (currentGroup.length) {
    groups.push({ label: `Bar ${currentBar}`, beats: currentGroup });
  }

  return groups;
}

export function BeatTable(props: BeatTableProps): HTMLElement {
  const content = document.createElement("div");
  content.className = "analysis-card analysis-beats";

  if (!props.beats.length) {
    const empty = document.createElement("p");
    empty.className = "muted";
    empty.textContent = "No beat data for current song.";
    content.appendChild(empty);
    return Card(content, { variant: "outlined" });
  }

  const groupsRoot = document.createElement("div");
  groupsRoot.className = "beats-groups";
  content.appendChild(groupsRoot);

  const status = document.createElement("p");
  status.className = "muted";
  content.appendChild(status);

  const groups = groupBeats(props.beats);
  let rendered = 0;

  const appendGroup = (group: BeatGroup) => {
    const section = document.createElement("section");
    section.className = "beat-group";

    const header = document.createElement("h4");
    header.textContent = group.label;
    section.appendChild(header);

    const table = document.createElement("table");
    table.className = "beat-table";

    const thead = document.createElement("thead");
    const headerRow = document.createElement("tr");
    ["Time", "Beat", "Type", "Bass", "Chord"].forEach(col => {
      const th = document.createElement("th");
      th.textContent = col;
      headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    for (const beat of group.beats) {
      const row = document.createElement("tr");
      const timeCell = document.createElement("td");
      timeCell.textContent = formatPosition(beat.time);
      row.appendChild(timeCell);

      const beatCell = document.createElement("td");
      beatCell.textContent = String(beat.beat);
      row.appendChild(beatCell);

      const typeCell = document.createElement("td");
      typeCell.textContent = beat.type;
      row.appendChild(typeCell);

      const bassCell = document.createElement("td");
      bassCell.textContent = beat.bass || "-";
      row.appendChild(bassCell);

      const chordCell = document.createElement("td");
      chordCell.textContent = beat.chord || "-";
      row.appendChild(chordCell);

      tbody.appendChild(row);
    }
    table.appendChild(tbody);

    section.appendChild(table);
    groupsRoot.appendChild(section);
  };

  const renderNextPage = () => {
    const next = groups.slice(rendered, rendered + BEAT_GROUP_PAGE_SIZE);
    for (const group of next) appendGroup(group);
    rendered += next.length;
    status.textContent = rendered < groups.length
      ? `Showing ${rendered} of ${groups.length} beat groups.`
      : `Showing all ${groups.length} beat groups.`;
  };

  const fillUntilScrollable = () => {
    while (rendered < groups.length && content.scrollHeight <= content.clientHeight) {
      renderNextPage();
    }
  };

  content.addEventListener("scroll", () => {
    if (rendered >= groups.length) return;
    const threshold = content.scrollHeight - content.clientHeight - 24;
    if (content.scrollTop >= threshold) {
      renderNextPage();
      fillUntilScrollable();
    }
  });

  renderNextPage();
  queueMicrotask(fillUntilScrollable);

  if (groups.length <= BEAT_GROUP_PAGE_SIZE) {
    status.textContent = `Showing all ${groups.length} beat groups.`;
  }

  return Card(content, { variant: "outlined" });
}
