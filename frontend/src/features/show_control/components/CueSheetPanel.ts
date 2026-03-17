import { Card } from "../../../shared/components/layout/Card.ts";
import { List } from "../../../shared/components/layout/List.ts";

type CueSection = {
  time: string;
  name: string;
  chasers: number;
  effects: number;
};

const CUES: CueSection[] = [
  { time: "0.00", name: "Intro", chasers: 2, effects: 5 },
  { time: "12.00", name: "Verse A", chasers: 5, effects: 0 },
  { time: "18.00", name: "Verse A", chasers: 5, effects: 0 },
  { time: "24.21", name: "Drop", chasers: 0, effects: 8 },
  { time: "24.70", name: "Verse B", chasers: 4, effects: 1 },
];

export function CueSheetPanel(): HTMLElement {
  const content = document.createElement("div");
  content.className = "show-control-body";
  const list = document.createElement("div");
  list.className = "show-control-list c-list";

  for (const cue of CUES) {
    const time = document.createElement("span");
    time.className = "u-cell u-cell-time mono";
    time.textContent = cue.time;

    const title = document.createElement("span");
    title.className = "cue-sheet-title u-cell u-cell-effect mono";
    title.textContent = cue.name;

    const meta = document.createElement("span");
    meta.className = "cue-sheet-meta muted";
    meta.textContent = `chasers:${cue.chasers} effects:${cue.effects}`;

    const contentCells = document.createElement("div");
    contentCells.append(time, title, meta);

    const row = List({
      className: "cue-sheet-row",
      content: contentCells,
      isActive: cue.time === "0.00",
    });
    list.appendChild(row);
  }
  content.appendChild(list);

  return Card(content, { variant: "outlined", className: "show-control-panel" });
}
