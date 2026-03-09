import { previewEffect } from "../fixture_intents.ts";
import type { FixtureVM } from "../adapters/fixture_vm.ts";

function effectOptions(fixture: FixtureVM): string[] {
  if (fixture.hasPanTilt) return ["flash", "strobe", "full", "move_to", "move_to_poi", "seek", "sweep"];
  if (fixture.hasRgb) return ["flash", "strobe", "full", "fade_in"];
  return ["flash", "strobe", "full"];
}

export function EffectTray(fixture: FixtureVM): HTMLElement {
  const root = document.createElement("div");
  root.className = "effect-tray";

  const topRow = document.createElement("div");
  topRow.className = "effect-tray-top";

  const select = document.createElement("select");
  select.className = "input effect-select";
  for (const effect of effectOptions(fixture)) {
    const option = document.createElement("option");
    option.value = effect;
    option.textContent = effect;
    select.appendChild(option);
  }

  const duration = document.createElement("input");
  duration.className = "input effect-duration";
  duration.type = "number";
  duration.min = "50";
  duration.step = "50";
  duration.value = "1000";

  topRow.append(select, duration);

  const paramsRow = document.createElement("div");
  paramsRow.className = "effect-params";
  const fromInput = document.createElement("input");
  fromInput.className = "input effect-param";
  fromInput.type = "number";
  fromInput.step = "1";
  fromInput.value = "1";
  fromInput.placeholder = "from";

  const toInput = document.createElement("input");
  toInput.className = "input effect-param";
  toInput.type = "number";
  toInput.step = "1";
  toInput.value = "0";
  toInput.placeholder = "to";

  paramsRow.append(fromInput, toInput);

  const preview = document.createElement("button");
  preview.type = "button";
  preview.className = "btn effect-preview";
  preview.textContent = "preview";
  preview.addEventListener("click", () => {
    const payload: Record<string, number> = {};
    const from = Number(fromInput.value);
    const to = Number(toInput.value);
    if (Number.isFinite(from)) payload.from = from;
    if (Number.isFinite(to)) payload.to = to;
    const durationMs = Math.max(50, Number(duration.value) || 1000);
    previewEffect(fixture.id, select.value, durationMs, payload);
  });

  root.append(topRow, paramsRow, preview);
  return root;
}
