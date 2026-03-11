import { Card } from "../../../shared/components/layout/Card.ts";

type SongPart = {
  time: string;
  name: string;
};

const SONG_PARTS: SongPart[] = [
  { time: "0.00", name: "Intro" },
  { time: "12.00", name: "Verse A" },
  { time: "24.21", name: "First Drop" },
  { time: "48.10", name: "Verse B" },
  { time: "72.30", name: "Final Drop" },
];

export function SongPartsPanel(): HTMLElement {
  const content = document.createElement("div");
  content.className = "show-control-body";

  const list = document.createElement("ol");
  list.className = "show-control-list mono";

  for (const part of SONG_PARTS) {
    const item = document.createElement("li");
    item.className = `show-control-row${part.time === "0.00" ? " is-active" : ""}`;

    const time = document.createElement("span");
    time.className = "show-control-time";
    time.textContent = part.time;

    const name = document.createElement("span");
    name.className = "show-control-label";
    name.textContent = part.name;

    item.append(time, name);
    list.appendChild(item);
  }

  content.appendChild(list);
  return Card(content, { variant: "outlined", className: "show-control-panel" });
}
