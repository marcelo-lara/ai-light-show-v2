import { throttle } from "../../../../shared/utils/throttle.ts";
import { setFixtureValues } from "../../fixture_intents.ts";
import { Slider } from "../../../../shared/components/controls/Slider.ts";
import { Dropdown } from "../../../../shared/components/controls/Dropdown.ts";
import type { FixtureVM } from "../../adapters/fixture_vm.ts";

export function StandardControls(fixture: FixtureVM) {
  const fixtureId = fixture.id;
  const values = fixture.values;
  const metaChannels = fixture.metaChannels;
  const mappings = fixture.mappings;

  const send = throttle((newValues: Record<string, number | string>) => {
    setFixtureValues(fixtureId, newValues);
  }, 16);

  const wrap = document.createElement("div");
  wrap.className = "control-stack";

  const controls: Record<string, any> = {};

  for (const [mcId, mc] of Object.entries(metaChannels)) {
    const currentValue = values[mcId] ?? (mc.kind === "u16" ? 0 : 0);
    
    if (mc.kind === "enum" && mc.mapping) {
      const mapping = mappings[mc.mapping] || {};
      const options = Object.keys(mapping).map(label => ({
        label,
        value: label // The backend expects labels for enum intents
      }));

      const dropdown = Dropdown({
        label: mc.label,
        value: String(currentValue),
        options,
        onChange: (val) => {
          send({ [mcId]: val });
        }
      });
      controls[mcId] = {
        update: (v: any) => {
           const select = dropdown.querySelector("select");
           if (select) select.value = String(v);
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
        value: Number(currentValue),
        onInput: (v) => send({ [mcId]: v }),
        onCommit: (v) => setFixtureValues(fixtureId, { [mcId]: v })
      });
      controls[mcId] = slider;
      wrap.appendChild(slider);
    } else if (mc.kind === "rgb") {
      // Skip RGB in StandardControls; handled by specialized RgbControls
      continue;
    }
  }

  (wrap as any).updateValues = (newValues: Record<string, number | string>) => {
    for (const [k, v] of Object.entries(newValues)) {
      if (controls[k]) {
        if (controls[k].setValue) {
           controls[k].setValue(Number(v));
        } else if (controls[k].update) {
           controls[k].update(v);
        }
      }
    }
  };

  return wrap;
}
