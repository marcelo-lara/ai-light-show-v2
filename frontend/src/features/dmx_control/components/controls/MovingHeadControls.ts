import { setFixtureValues } from "../../fixture_intents.ts";
import { PanTiltControl } from "./PanTiltControl.ts";
import { PoiLocationController } from "./PoiLocationController.ts";
import { StandardControls } from "./StandardControls.ts";
import type { FixtureVM } from "../../adapters/fixture_vm.ts";
import type { FixtureControlHandle, FixtureValues } from "./control_types.ts";

export function MovingHeadControls(fixture: FixtureVM): FixtureControlHandle {
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
  let refreshPoiController = () => {};

  const wrap = document.createElement("div");
  wrap.className = "moving-head-layout";

  const spatialCol = document.createElement("div");
  spatialCol.className = "moving-head-spatial";

  const channelsCol = document.createElement("div");
  channelsCol.className = "moving-head-channels";

  let ptControl: ReturnType<typeof PanTiltControl> | null = null;
  let selectedPoiTarget: { pan: number; tilt: number } | null = null;
  if (hasPanTilt) {
    // Add 2D Pan/Tilt Control
    ptControl = PanTiltControl({
      fixtureId,
      initialPan: Number(state.pan),
      initialTilt: Number(state.tilt),
      maxPan,
      maxTilt,
      poiPan: null,
      poiTilt: null,
      onChange: (pan, tilt) => {
        state.pan = pan;
        state.tilt = tilt;
        refreshPoiController();
      },
      onCommit: (pan, tilt) => {
        state.pan = pan;
        state.tilt = tilt;
        setFixtureValues(fixtureId, { pan, tilt });
      },
    });
    spatialCol.appendChild(ptControl.root);
  }

  // Add POI Button Grid
  const poiController = PoiLocationController({
    fixtureId,
    getLivePanTilt: () => ({
      pan: Number(state.pan ?? 0),
      tilt: Number(state.tilt ?? 0),
    }),
    setRefreshHandler: (refresh) => {
      refreshPoiController = refresh;
    },
    onSelectedPoiTargetChange: (target) => {
      selectedPoiTarget = target;
      if (ptControl) {
        ptControl.updatePoiTarget(
          selectedPoiTarget ? Number(selectedPoiTarget.pan) : null,
          selectedPoiTarget ? Number(selectedPoiTarget.tilt) : null,
        );
      }
    },
  });
  spatialCol.appendChild(poiController.root);

  // Use StandardControls for all other meta-channels (dimmer, strobe, color, gobo, etc.)
  const standard = StandardControls(fixture);
  channelsCol.appendChild(standard.root);
  wrap.append(spatialCol, channelsCol);

  const updateValues = (newValues: FixtureValues) => {
    if (ptControl) {
      const nextPan = newValues.pan !== undefined ? Number(newValues.pan) : Number(state.pan ?? 0);
      const nextTilt = newValues.tilt !== undefined ? Number(newValues.tilt) : Number(state.tilt ?? 0);
      if (newValues.pan !== undefined || newValues.tilt !== undefined) {
        state.pan = nextPan;
        state.tilt = nextTilt;
        ptControl.updatePanTilt(nextPan, nextTilt);
      }
    }
    standard.updateValues(newValues);
  };

  const dispose = () => {
    ptControl?.dispose();
    poiController.dispose();
    standard.dispose();
  };

  return {
    root: wrap,
    updateValues,
    dispose,
  };
}
