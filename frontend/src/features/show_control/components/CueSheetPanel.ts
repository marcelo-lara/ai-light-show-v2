import { Card } from "../../../shared/components/layout/Card.ts";

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

  for (const cue of CUES) {
    const row = document.createElement("article");
    row.className = `cue-sheet-row${cue.time === "0.00" ? " is-active" : ""}`;

    const title = document.createElement("p");
    title.className = "cue-sheet-title mono";
    title.textContent = `${cue.time} ${cue.name}`;

    const meta = document.createElement("p");
    meta.className = "cue-sheet-meta muted";
    meta.textContent = `chasers:${cue.chasers} effects:${cue.effects}`;

    row.append(title, meta);
    content.appendChild(row);
  }

  return Card(content, { variant: "outlined", className: "show-control-panel" });
}
