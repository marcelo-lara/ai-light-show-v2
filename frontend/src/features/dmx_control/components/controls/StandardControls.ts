import { throttle } from "../../../../shared/utils/throttle.ts";
import { setFixtureValues } from "../../fixture_intents.ts";
import { Slider } from "../../../../shared/components/controls/Slider.ts";
import { Dropdown } from "../../../../shared/components/controls/Dropdown.ts";
import type { FixtureVM } from "../../adapters/fixture_vm.ts";
import type { FixtureControlHandle, FixtureValues } from "./control_types.ts";

type ControlUpdater = (value: number | string) => void;

export function StandardControls(fixture: FixtureVM): FixtureControlHandle {
  const fixtureId = fixture.id;
  const values = fixture.values;
  const metaChannels = fixture.metaChannels;
  const mappings = fixture.mappings;

  const send = throttle((newValues: Record<string, number | string>) => {
    setFixtureValues(fixtureId, newValues);
  }, 16);

  const wrap = document.createElement("div");
  wrap.className = "control-stack";

  const updaters: Record<string, ControlUpdater> = {};
  const disposers: Array<() => void> = [];

  for (const [mcId, mc] of Object.entries(metaChannels)) {
    const currentValue = values[mcId] ?? (mc.kind === "u16" ? 0 : 0);

    if (mc.kind === "enum" && mc.mapping) {
      const mapping = mappings[mc.mapping] || {};
      const options = Object.entries(mapping).map(([_val, label]) => ({
        label: String(label), // The descriptive name (e.g. "Red")
        value: String(label), // The backend expects the label for set_values intent
      }));

      const dropdown = Dropdown({
        label: mc.label,
        value: String(currentValue),
        options,
        onChange: (val) => {
          send({ [mcId]: val });
        },
      });
      const select = dropdown.querySelector("select");
      updaters[mcId] = (value) => {
        if (select instanceof HTMLSelectElement) {
          select.value = String(value);
        }
      };
      wrap.appendChild(dropdown);
    } else if (mc.kind === "u8" || mc.kind === "u16") {
      // Skip pan/tilt if they are handled by a specialized XY pad (handled in MovingHeadControls)
      if (fixture.hasPanTilt && (mcId === "pan" || mcId === "tilt")) continue;

      const slider = Slider({
        label: mc.label,
        min: mc.min ?? 0,
        max: mc.max ?? (mc.kind === "u16" ? 65535 : 255),
        step: 1,
        value: Number(currentValue),
        onInput: (v) => send({ [mcId]: v }),
        onCommit: (v) => setFixtureValues(fixtureId, { [mcId]: v }),
      });
      updaters[mcId] = (value) => slider.setValue(Number(value));
      disposers.push(slider.dispose);
      wrap.appendChild(slider.root);
    } else if (mc.kind === "rgb") {
      // Skip RGB in StandardControls; handled by specialized RgbControls
      continue;
    }
  }

  const updateValues = (newValues: FixtureValues) => {
    for (const [k, v] of Object.entries(newValues)) {
      const updater = updaters[k];
      if (updater) {
        updater(v);
      }
    }
  };

  const dispose = () => {
    for (const cleanup of disposers) {
      cleanup();
    }
  };

  return {
    root: wrap,
    updateValues,
    dispose,
  };
}
