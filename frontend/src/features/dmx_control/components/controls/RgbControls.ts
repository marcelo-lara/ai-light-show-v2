import { throttle } from "../../../../shared/utils/throttle.ts";
import { setFixtureValues } from "../../fixture_intents.ts";

export function RgbControls(fixtureId: string) {
  const send = throttle((values: Record<string, number>) => {
    setFixtureValues(fixtureId, values);
  }, 16);

  // TODO: implement UIX rendering
  // Sliders: dimmer, red, green, blue
  // on input -> send({red:..., green:..., blue:...})
  // on release -> send final immediately (may call setFixtureValues directly)
  return { send };
}
