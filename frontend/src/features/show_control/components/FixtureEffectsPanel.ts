import { Card } from "../../../shared/components/layout/Card.ts";

const EFFECT_ROWS = [
  "0.00 ParCan L Fade B 1 to 0",
  "0.00 ParCan R Fade B 1 to 0",
  "12.00 Beam 1 Strobe 4Hz",
  "12.00 Beam 2 Strobe 4Hz",
  "24.21 Wash Center Pulse 2 bars",
  "24.70 ParCan L Fade B 0 to 1",
  "24.70 ParCan R Fade B 0 to 1",
  "48.10 Beam 1 Tilt Sweep",
  "48.10 Beam 2 Tilt Sweep",
  "72.30 Wash Center Flash",
  "72.30 Wash Side Flash",
  "84.00 Beam 1 Dimmer Fade Out",
];

export function FixtureEffectsPanel(): HTMLElement {
  const content = document.createElement("div");
  content.className = "show-control-body";

  const list = document.createElement("ol");
  list.className = "fixture-effects-list mono";

  for (const effect of EFFECT_ROWS) {
    const item = document.createElement("li");
    item.className = `fixture-effects-row${effect.startsWith("0.00") ? " is-active" : ""}`;
    item.textContent = effect;
    list.appendChild(item);
  }

  content.appendChild(list);
  return Card(content, { variant: "outlined", className: "show-control-panel" });
}
