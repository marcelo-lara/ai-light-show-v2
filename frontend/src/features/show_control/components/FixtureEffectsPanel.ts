import { Card } from "../../../shared/components/layout/Card.ts";
import { List } from "../../../shared/components/layout/List.ts";

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

  const list = document.createElement("div");
  list.className = "fixture-effects-list o-list";

  for (const effect of EFFECT_ROWS) {
    const [timeToken, ...rest] = effect.split(" ");
    const time = document.createElement("span");
    time.className = "u-cell u-cell-time";
    time.textContent = timeToken ?? "0.00";

    const details = document.createElement("span");
    details.className = "fixture-effects-row-details u-cell u-cell-effect";
    details.textContent = rest.join(" ");

    const item = List({
      className: "fixture-effects-row",
      content: [time, details],
      isActive: effect.startsWith("0.00"),
    });
    list.appendChild(item);
  }

  content.appendChild(list);
  return Card(content, {
    ariaLabel: "Fixture Effects panel",
    variant: "outlined",
    className: "show-control-panel",
  });
}
