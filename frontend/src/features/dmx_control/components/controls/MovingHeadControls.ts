import { throttle } from "../../../../shared/utils/throttle.ts";
import { setFixtureValues } from "../../fixture_intents.ts";
import { Slider } from "../../../../shared/components/controls/Slider.ts";

export function MovingHeadControls(fixtureId: string) {
  const state = { pan: 128, tilt: 128, dimmer: 255, strobe: 0 };
  const send = throttle((values: Record<string, number>) => {
    setFixtureValues(fixtureId, values);
  }, 16);

  const wrap = document.createElement("div");
  wrap.className = "control-stack";

  for (const key of ["pan", "tilt", "dimmer", "strobe"] as const) {
    wrap.appendChild(
      Slider({
        label: key,
        min: 0,
        max: 255,
        value: state[key],
        onInput: (value) => {
          state[key] = value;
          send({ ...state });
        },
        onCommit: (value) => {
          state[key] = value;
          setFixtureValues(fixtureId, { ...state });
        },
      }),
    );
  }

  return wrap;
}
