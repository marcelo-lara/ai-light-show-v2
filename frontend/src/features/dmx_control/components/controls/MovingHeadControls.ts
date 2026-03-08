import { throttle } from "../../../../shared/utils/throttle.ts";
import { setFixtureValues } from "../../fixture_intents.ts";
import { Slider } from "../../../../shared/components/controls/Slider.ts";
import { PanTiltControl } from "./PanTiltControl.ts";
import { PoiLocationController } from "./PoiLocationController.ts";
import { StandardControls } from "./StandardControls.ts";
import type { FixtureVM } from "../../adapters/fixture_vm.ts";

export function MovingHeadControls(fixture: FixtureVM) {
  const fixtureId = fixture.id;

  // Semantic mapping from backend refactor
  const hasPanTilt = fixture.metaChannels.pan && fixture.metaChannels.tilt;
  const panMC = fixture.metaChannels.pan;
  const tiltMC = fixture.metaChannels.tilt;

  const maxPan = panMC?.kind === "u16" ? 65535 : 255;
  const maxTilt = tiltMC?.kind === "u16" ? 65535 : 255;

  const state: Record<string, number | string> = {
    pan: Number(fixture.values.pan ?? (maxPan / 2)),
    tilt: Number(fixture.values.tilt ?? (maxTilt / 2)),
  };

  const wrap = document.createElement("div");
  wrap.className = "control-stack";

  let ptControl: any;
  if (hasPanTilt) {
    // Add 2D Pan/Tilt Control
    ptControl = PanTiltControl({
      fixtureId,
      initialPan: Number(state.pan),
      initialTilt: Number(state.tilt),
      maxPan,
      maxTilt,
      onCommit: (pan, tilt) => {
        state.pan = pan;
        state.tilt = tilt;
        setFixtureValues(fixtureId, { pan, tilt });
      }
    });
    wrap.appendChild(ptControl);
  }

  // Add POI Button Grid
  wrap.appendChild(PoiLocationController({ fixtureId }));

  // Use StandardControls for all other meta-channels (dimmer, strobe, color, gobo, etc.)
  const standard = StandardControls(fixture);
  wrap.appendChild(standard);

  // Handle external updates
  (wrap as any).updateValues = (newValues: Record<string, number | string>) => {
    if (ptControl && newValues.pan !== undefined && newValues.tilt !== undefined) {
      ptControl.updatePanTilt(Number(newValues.pan), Number(newValues.tilt));
    }
    if ((standard as any).updateValues) {
      (standard as any).updateValues(newValues);
    }
  };

  return wrap;
}
