import { previewEffect } from "../fixture_intents.ts";
import type { FixtureVM } from "../adapters/fixture_vm.ts";
import { Button } from "../../../shared/components/controls/Button.ts";
import { Dropdown } from "../../../shared/components/controls/Dropdown.ts";
import { Slider } from "../../../shared/components/controls/Slider.ts";

function effectOptions(fixture: FixtureVM): string[] {
  if (fixture.hasPanTilt) return ["flash", "strobe", "full", "move_to", "move_to_poi", "seek", "sweep"];
  if (fixture.hasRgb) return ["flash", "strobe", "full", "fade_in"];
  return ["flash", "strobe", "full"];
}

export function EffectTray(fixture: FixtureVM): HTMLElement {
  const root = document.createElement("div");
  root.className = "effect-tray";
  root.setAttribute("aria-label", `${fixture.name} effect preview`);

  const topRow = document.createElement("div");
  topRow.className = "effect-tray-top";

  const effects = effectOptions(fixture);
  const effectControl = Dropdown({
    value: effects[0] ?? "",
    options: effects.map((effect) => ({ value: effect, label: effect })),
    attributes: { "aria-label": "Preview effect type" },
  });
  const durationControl = Slider({
    label: "Duration",
    min: 50,
    max: 5000,
    step: 50,
    value: 1000,
    className: "effect-duration",
    onInput: () => {},
  });

  topRow.append(effectControl.root, durationControl.root);

  const paramsRow = document.createElement("div");
  paramsRow.className = "effect-params";
  const fromControl = Slider({
    label: "From",
    min: 0,
    max: 255,
    step: 1,
    value: 1,
    className: "effect-param",
    onInput: () => {},
  });

  const toControl = Slider({
    label: "To",
    min: 0,
    max: 255,
    step: 1,
    value: 0,
    className: "effect-param",
    onInput: () => {},
  });

  paramsRow.append(fromControl.root, toControl.root);

  const preview = Button({
    caption: "Preview",
    state: "default",
    bindings: {
      title: "Preview effect",
      onClick: () => {
    const payload: Record<string, number> = {};
    const from = Number(fromControl.input.value);
    const to = Number(toControl.input.value);
    if (Number.isFinite(from)) payload.from = from;
    if (Number.isFinite(to)) payload.to = to;
    const durationMs = Math.max(50, Number(durationControl.input.value) || 1000);
    previewEffect(fixture.id, effectControl.select.value, durationMs, payload);
      },
    },
  });

  root.append(topRow, paramsRow, preview);
  return root;
}
