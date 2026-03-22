import { throttle } from "../../../../shared/utils/throttle.ts";
import { setFixtureValues } from "../../fixture_intents.ts";
import { Slider } from "../../../../shared/components/controls/Slider.ts";
import { Dropdown } from "../../../../shared/components/controls/Dropdown.ts";
import type { FixtureVM } from "../../adapters/fixture_vm.ts";
import type { FixtureControlHandle, FixtureValues } from "./control_types.ts";
import { EnumGrid } from "./EnumGrid.ts";

type ControlUpdater = (value: number | string) => void;
type MappingOption = { key: string; label: string };

function mappingOptions(mapping: Record<string, number | string>): MappingOption[] {
  return Object.entries(mapping).map(([key, label]) => ({ key: String(key), label: String(label) }));
}

function sortByNumericKey(options: MappingOption[]): MappingOption[] {
  return [...options].sort((a, b) => Number(a.key) - Number(b.key));
}

function isInlineWheelControl(fixture: FixtureVM, mcId: string): boolean {
  if (!fixture.hasPanTilt) return false;
  return mcId === "color" || mcId === "gobo" || mcId === "prism";
}

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
  const inlineWheelControls: HTMLElement[] = [];
  const wheelControls: HTMLElement[] = [];
  const rangeControls: HTMLElement[] = [];

  for (const [mcId, mc] of Object.entries(metaChannels)) {
    if (mc.hidden) continue;
    const currentValue = values[mcId] ?? (mc.kind === "u16" ? 0 : 0);

    if (mc.kind === "enum" && mc.mapping && mc.step === true && isInlineWheelControl(fixture, mcId)) {
      const mapping = mappings[mc.mapping] || {};
      const options = sortByNumericKey(mappingOptions(mapping)).map((option) => ({
        label: option.label,
        value: option.label,
      }));

      const dropdown = Dropdown({
        label: mc.label,
        value: String(currentValue),
        options,
        onChange: (val) => {
          send({ [mcId]: val });
        },
      });
      updaters[mcId] = (value) => {
        dropdown.setValue(String(value));
      };
      inlineWheelControls.push(dropdown.root);
    } else if (mc.kind === "enum" && mc.mapping) {
      const mapping = mappings[mc.mapping] || {};
      const options = sortByNumericKey(mappingOptions(mapping)).map((option) => ({
        label: option.label,
        value: option.label,
      }));

      const enumGrid = EnumGrid({
        label: mc.label,
        value: String(currentValue),
        options,
        onChange: (val) => {
          send({ [mcId]: val });
        },
      });
      updaters[mcId] = (value) => {
        enumGrid.setValue(String(value));
      };
      disposers.push(enumGrid.dispose);
      wheelControls.push(enumGrid.root);
    } else if (mc.kind === "u8" && mc.mapping && mc.step === true) {
      const mapping = mappings[mc.mapping] || {};
      const options = sortByNumericKey(mappingOptions(mapping));
      const grid = EnumGrid({
        label: mc.label,
        value: String(currentValue),
        options: options.map((option) => ({
          label: option.label,
          value: option.key,
        })),
        onChange: (val) => {
          const parsed = Number(val);
          if (Number.isFinite(parsed)) {
            send({ [mcId]: parsed });
          }
        },
      });
      updaters[mcId] = (value) => grid.setValue(String(value));
      disposers.push(grid.dispose);
      wheelControls.push(grid.root);
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
      rangeControls.push(slider.root);
    } else if (mc.kind === "rgb") {
      // Skip RGB in StandardControls; handled by specialized RgbControls
      continue;
    }
  }

  wrap.append(...inlineWheelControls, ...wheelControls, ...rangeControls);

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
