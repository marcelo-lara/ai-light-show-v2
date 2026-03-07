import { throttle } from "../../../../shared/utils/throttle.ts";
import { setFixtureValues } from "../../fixture_intents.ts";
import { Slider } from "../../../../shared/components/controls/Slider.ts";
import type { FixtureVM } from "../../adapters/fixture_vm.ts";

export function RgbControls(fixture: FixtureVM) {
  const fixtureId = fixture.id;
  
  // Use property names provided by backend (e.g., 'dim', 'red', 'green', 'blue')
  const state: Record<string, number> = {};
  const keys = Object.keys(fixture.values);
  
  for (const k of keys) {
    state[k] = fixture.values[k] ?? 0;
  }

  const send = throttle((values: Record<string, number>) => {
    setFixtureValues(fixtureId, values);
  }, 16);

  const wrap = document.createElement("div");
  wrap.className = "control-stack";

  const sliders: Record<string, any> = {};
  for (const key of keys) {
    const s = Slider({
      label: key,
      min: 0,
      max: 255,
      value: state[key],
      onInput: (value) => {
        state[key] = value;
        send({ [key]: value });
      },
      onCommit: (value) => {
        state[key] = value;
        setFixtureValues(fixtureId, { [key]: value });
      },
    });
    sliders[key] = s;
    wrap.appendChild(s);
  }

  // Handle external updates
  (wrap as any).updateValues = (newValues: Record<string, number>) => {
    for (const [k, v] of Object.entries(newValues)) {
      if (sliders[k]) {
        sliders[k].setValue(v);
      }
    }
  };

  return wrap;
}
