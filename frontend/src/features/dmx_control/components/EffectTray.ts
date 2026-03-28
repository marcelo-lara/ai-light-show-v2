import { previewEffect } from "../fixture_intents.ts";
import type { FixtureVM } from "../adapters/fixture_vm.ts";
import { getBackendStore } from "../../../shared/state/backend_state.ts";
import { Button } from "../../../shared/components/controls/Button.ts";
import { Dropdown } from "../../../shared/components/controls/Dropdown.ts";
import { Input } from "../../../shared/components/controls/Input.ts";
import { ParamForm } from "../../show_builder/components/effect_params/ParamForm.ts";
import { getDefaultParams } from "../../show_builder/components/effect_params/params_schema.ts";

function effectOptions(fixture: FixtureVM): string[] {
  if (fixture.supportedEffects.length > 0) return fixture.supportedEffects.map((effect) => effect.id);
  if (fixture.hasPanTilt) return ["flash", "strobe", "full", "move_to", "move_to_poi", "seek", "sweep"];
  if (fixture.hasRgb) return ["flash", "strobe", "full", "fade_in"];
  return ["flash", "strobe", "full"];
}

function effectControlOptions(fixture: FixtureVM): Array<{ value: string; label: string }> {
  if (fixture.supportedEffects.length > 0) {
    return fixture.supportedEffects.map((effect) => ({ value: effect.id, label: effect.label }));
  }
  return effectOptions(fixture).map((effect) => ({ value: effect, label: effect }));
}

export function EffectTray(fixture: FixtureVM): HTMLElement {
  const root = document.createElement("div");
  root.className = "effect-tray";

  const topRow = document.createElement("div");
  topRow.className = "effect-tray-top";

  const effects = effectOptions(fixture);
  let selectedEffect = effects[0] ?? "";
  let params = getDefaultParams(selectedEffect, fixture.type);
  const effectControl = Dropdown({
    value: selectedEffect,
    options: effectControlOptions(fixture),
    attributes: { "aria-label": "Preview effect" },
    onChange: (value) => {
      selectedEffect = value;
      params = getDefaultParams(value, fixture.type);
      renderParams();
    },
  });
  const durationControl = Input({
    caption: "Duration",
    bindings: {
      type: "number",
      value: "1000",
      min: 50,
      max: 5000,
      step: 50,
      inputMode: "numeric",
      className: "effect-duration",
      attributes: { "aria-label": "Effect duration in milliseconds" },
    },
  });

  topRow.append(effectControl.root, durationControl.root);

  const paramsRow = document.createElement("div");
  paramsRow.className = "effect-params";

  const renderParams = () => {
    paramsRow.replaceChildren(ParamForm({
      effectName: selectedEffect,
      fixtureType: fixture.type,
      values: params,
      pois: getBackendStore().state.pois ?? [],
      onChange: (name, value) => {
        params[name] = value;
      },
    }));
  };

  renderParams();

  const preview = Button({
    caption: "Preview",
    state: "default",
    bindings: {
      title: "Preview effect",
      onClick: () => {
        const durationMs = Math.max(50, Number(durationControl.input.value) || 1000);
        previewEffect(fixture.id, selectedEffect, durationMs, params);
      },
    },
  });

  root.append(topRow, paramsRow, preview);
  return root;
}
