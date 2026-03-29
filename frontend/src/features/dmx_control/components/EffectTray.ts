import { previewEffect } from "../fixture_intents.ts";
import type { FixtureVM } from "../adapters/fixture_vm.ts";
import { getBackendStore } from "../../../shared/state/backend_state.ts";
import { Button } from "../../../shared/components/controls/Button.ts";
import { Dropdown } from "../../../shared/components/controls/Dropdown.ts";
import { Input } from "../../../shared/components/controls/Input.ts";
import { ParamForm } from "../../show_builder/components/effect_params/ParamForm.ts";
import { getDefaultDurationSeconds, getDefaultParams } from "../../show_builder/components/effect_params/params_schema.ts";

function effectOptions(fixture: FixtureVM): string[] {
  if (fixture.supportedEffects.length > 0) return fixture.supportedEffects.map((effect) => effect.id);
  if (fixture.hasPanTilt) return ["flash", "strobe", "full", "move_to", "move_to_poi", "orbit", "sweep"];
  if (fixture.hasRgb) return ["flash", "strobe", "full", "fade_in"];
  return ["flash", "strobe", "full"];
}

function defaultDurationMs(effectName: string, fixtureType: string): number {
  const state = getBackendStore().state;
  const bpm = Number(state.playback?.bpm ?? state.song?.bpm ?? 0);
  return Math.max(50, Math.round(getDefaultDurationSeconds(effectName, bpm, fixtureType) * 1000));
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
  let durationMs = defaultDurationMs(selectedEffect, fixture.type);
  const effectControl = Dropdown({
    value: selectedEffect,
    options: effectControlOptions(fixture),
    attributes: { "aria-label": "Preview effect" },
    onChange: (value) => {
      selectedEffect = value;
      params = getDefaultParams(value, fixture.type);
      durationMs = defaultDurationMs(value, fixture.type);
      durationControl.input.value = String(durationMs);
      renderParams();
    },
  });
  const durationControl = Input({
    caption: "Duration",
    bindings: {
      type: "number",
      value: String(durationMs),
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
        const durationMs = Math.max(50, Number(durationControl.input.value) || defaultDurationMs(selectedEffect, fixture.type));
        previewEffect(fixture.id, selectedEffect, durationMs, params);
      },
    },
  });

  root.append(topRow, paramsRow, preview);
  return root;
}
