import { throttle } from "../../../../shared/utils/throttle.ts";
import { setFixtureValues } from "../../fixture_intents.ts";

export function MovingHeadControls(fixtureId: string) {
  const send = throttle((values: Record<string, number>) => {
    setFixtureValues(fixtureId, values);
  }, 16);

  // TODO: implement UIX rendering
  // XY pad -> pan/tilt, dimmer, strobe/shutter, wheels if available
  return { send };
}
