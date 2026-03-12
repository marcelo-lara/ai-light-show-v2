import { Card } from "../../../shared/components/layout/Card.ts";

type BeatTableProps = {
  beats: number[];
  downbeats: number[];
};

type BeatGroup = {
  label: string;
  beats: number[];
};

const BEAT_GROUP_PAGE_SIZE = 4;

function groupBeats(beats: number[], downbeats: number[]): BeatGroup[] {
  if (!beats.length) return [];
  if (!downbeats.length) {
    const groups: BeatGroup[] = [];
    for (let index = 0; index < beats.length; index += 4) {
      groups.push({ label: `Bar ${groups.length + 1}`, beats: beats.slice(index, index + 4) });
    }
    return groups;
  }

  const groups: BeatGroup[] = [];
  const firstDownbeat = downbeats[0];
  const pickup = beats.filter((beat) => beat < firstDownbeat);
  if (pickup.length) groups.push({ label: "Pickup", beats: pickup });

  for (let index = 0; index < downbeats.length; index++) {
    const start = downbeats[index];
    const end = downbeats[index + 1] ?? Number.POSITIVE_INFINITY;
    const barBeats = beats.filter((beat) => beat >= start && beat < end);
    if (!barBeats.length) continue;
    groups.push({ label: `Bar ${index + 1}`, beats: barBeats });
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

  const groups = groupBeats(props.beats, props.downbeats);
  let rendered = 0;

  const appendGroup = (group: BeatGroup) => {
    const section = document.createElement("section");
    section.className = "beat-group";

    const row = document.createElement("div");
    row.className = "beat-group-row";
    row.style.setProperty("--beat-count", String(Math.max(group.beats.length, 1)));

    for (const [index, beat] of group.beats.entries()) {
      const cell = document.createElement("span");
      cell.className = `beats-cell${index === 0 && group.label !== "Pickup" ? " is-downbeat" : ""}`;
      cell.textContent = beat.toFixed(3);
      row.appendChild(cell);
    }

    section.appendChild(row);
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
