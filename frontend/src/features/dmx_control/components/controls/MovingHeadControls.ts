import { throttle } from "../../../../shared/utils/throttle.ts";
import { setFixtureValues } from "../../fixture_intents.ts";
import { Slider } from "../../../../shared/components/controls/Slider.ts";
import { PanTiltControl } from "./PanTiltControl.ts";
import { PoiLocationController } from "./PoiLocationController.ts";
import type { FixtureVM } from "../../adapters/fixture_vm.ts";

export function MovingHeadControls(fixture: FixtureVM) {
  const fixtureId = fixture.id;

  // Semantic mapping from backend refactor
  // Use property names provided by backend (e.g., 'pan', 'tilt', 'dim', 'shutter')
  // For 'pan_tilt', decide bits based on value range or assumed 16-bit for moving heads
  const is16Bit = true; // Moving heads use 16-bit in our new backend logic
  const maxPT = is16Bit ? 65535 : 255;

  const state: Record<string, number> = {
    pan: fixture.values.pan ?? (maxPT / 2),
    tilt: fixture.values.tilt ?? (maxPT / 2),
  };

  // Dynamically add other sliders based on what's in fixture.values
  // but exclude pan/tilt which are handled by the 2D surface
  const otherKeys = Object.keys(fixture.values).filter(k => !['pan', 'tilt'].includes(k));
  for (const k of otherKeys) {
    state[k] = fixture.values[k];
  }

  const send = throttle((values: Record<string, number>) => {
    setFixtureValues(fixtureId, values);
  }, 16);

  const wrap = document.createElement("div");
  wrap.className = "control-stack";

  // Add 2D Pan/Tilt Control
  const ptControl = PanTiltControl({
    fixtureId,
    initialPan: state.pan,
    initialTilt: state.tilt,
    maxPan: maxPT,
    maxTilt: maxPT,
    onCommit: (pan, tilt) => {
      state.pan = pan;
      state.tilt = tilt;
      setFixtureValues(fixtureId, { pan, tilt });
    }
  });
  wrap.appendChild(ptControl);

  // Add POI Button Grid
  wrap.appendChild(PoiLocationController({ fixtureId }));

  // Add dynamic sliders for all other attributes (dim, strobe, color, gobo, etc.)
  const sliders: Record<string, any> = {};
  for (const key of otherKeys) {
    const s = Slider({
      label: key,
      min: 0,
      max: 255, // most attributes are 8-bit
      step: 1,
      value: state[key],
      onInput: (value: number) => {
        state[key] = value;
        send({ [key]: value });
      },
    });
    sliders[key] = s;
    wrap.appendChild(s);
  }

  // Handle external updates
  (wrap as any).updateValues = (newValues: Record<string, number>) => {
    if (newValues.pan !== undefined && newValues.tilt !== undefined) {
      (ptControl as any).updatePanTilt(newValues.pan, newValues.tilt);
    }
    for (const [k, v] of Object.entries(newValues)) {
      if (sliders[k]) {
        sliders[k].setValue(v);
      }
    }
  };

  return wrap;
}
