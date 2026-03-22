import { getBackendStore, subscribeBackendStore } from "../../../../shared/state/backend_state.ts";
import { setFixtureValues, updatePoiFixtureTarget } from "../../fixture_intents.ts";
import { Dropdown } from "../../../../shared/components/controls/Dropdown.ts";
import { Button } from "../../../../shared/components/controls/Button.ts";
import { ConfirmCancelPrompt } from "../../../../shared/components/feedback/ConfirmCancelPrompt.ts";
import type { DisposableElementHandle } from "./control_types.ts";
import type { FixturePoiTarget } from "./poi_helpers.ts";
import { hasFixtureTargetDiff, normalizePois } from "./poi_helpers.ts";

export interface PoiLocationControllerOptions {
  fixtureId: string;
  getLivePanTilt?: () => { pan: number; tilt: number };
  onSelectedPoiTargetChange?: (target: FixturePoiTarget | null) => void;
  setRefreshHandler?: (refresh: () => void) => void;
}

export function PoiLocationController(
  { fixtureId, getLivePanTilt, onSelectedPoiTargetChange, setRefreshHandler }: PoiLocationControllerOptions,
): DisposableElementHandle {
  const container = document.createElement("div");
  container.className = "poi-controller-row";

  let currentSelectedPoiId = "";
  let selectedPoiTarget: FixturePoiTarget | null = null;
  let optimisticSetVisibility: "hide_once" | "show_once" | null = null;
  let postSelectTimer: number | null = null;

  const render = () => {
    container.replaceChildren();

    const store = getBackendStore();
    const pois = normalizePois(store.state.pois);
    const fixtureState = store.state.fixtures?.[fixtureId];
    const snapshotPan = Number(fixtureState?.values?.["pan"] ?? 0);
    const snapshotTilt = Number(fixtureState?.values?.["tilt"] ?? 0);
    const live = getLivePanTilt?.();
    const currentPan = Number(live?.pan ?? snapshotPan);
    const currentTilt = Number(live?.tilt ?? snapshotTilt);

    const dropdownWrap = document.createElement("div");
    dropdownWrap.className = "poi-dropdown-wrap";

    const options = pois.map((p) => ({
      label: p.name,
      value: p.id,
    }));

    if (options.length > 0 && !currentSelectedPoiId) {
      currentSelectedPoiId = options[0].value;
    } else if (currentSelectedPoiId && !options.some((option) => option.value === currentSelectedPoiId)) {
      currentSelectedPoiId = options[0]?.value ?? "";
      optimisticSetVisibility = null;
    }

    const resolveTarget = (poiId: string): FixturePoiTarget | null => {
      const poi = pois.find((p) => p.id === poiId);
      const target = poi?.fixtures?.[fixtureId];
      if (!target) return null;
      return {
        pan: Number(target.pan ?? 0),
        tilt: Number(target.tilt ?? 0),
      };
    };

    const resolvePoiName = (poiId: string): string => {
      const poi = pois.find((entry) => entry.id === poiId);
      return poi?.name ?? poiId;
    };

    selectedPoiTarget = currentSelectedPoiId ? resolveTarget(currentSelectedPoiId) : null;
    onSelectedPoiTargetChange?.(selectedPoiTarget);

    const dropdown = Dropdown({
      value: currentSelectedPoiId,
      options,
      onChange: (val) => {
        currentSelectedPoiId = val;

        const newTarget = resolveTarget(val);
        selectedPoiTarget = newTarget;
        onSelectedPoiTargetChange?.(newTarget);

        if (!newTarget) {
          optimisticSetVisibility = "show_once";
          setFixtureValues(fixtureId, { pan: 0, tilt: 0 });
        } else {
          optimisticSetVisibility = "hide_once";
          setFixtureValues(fixtureId, { pan: newTarget.pan, tilt: newTarget.tilt });
        }

        render();
        if (postSelectTimer !== null) {
          globalThis.clearTimeout(postSelectTimer);
        }
        postSelectTimer = globalThis.setTimeout(() => {
          postSelectTimer = null;
          render();
        }, 120);
      },
    });
    dropdownWrap.appendChild(dropdown.root);
    container.appendChild(dropdownWrap);

    const showSet = (() => {
      if (!currentSelectedPoiId) return false;
      if (optimisticSetVisibility === "hide_once") {
        optimisticSetVisibility = null;
        return false;
      }
      if (optimisticSetVisibility === "show_once") {
        optimisticSetVisibility = null;
        return true;
      }
      return hasFixtureTargetDiff(selectedPoiTarget ?? undefined, currentPan, currentTilt);
    })();

    if (showSet) {
      const setBtn = Button({
        caption: "Set",
        state: "default",
        bindings: {
          onClick: () => {
            void (async () => {
              const shouldConfirmOverwrite = selectedPoiTarget !== null;
              if (shouldConfirmOverwrite) {
                const confirmed = await ConfirmCancelPrompt({
                  title: "Overwrite POI target",
                  message: `Overwrite the saved target for '${resolvePoiName(currentSelectedPoiId)}' on fixture '${fixtureId}' with the current pan/tilt values?`,
                  confirmLabel: "Overwrite",
                  cancelLabel: "Cancel",
                });
                if (!confirmed) return;
              }

              updatePoiFixtureTarget(currentSelectedPoiId, fixtureId, currentPan, currentTilt);
              selectedPoiTarget = { pan: currentPan, tilt: currentTilt };
              optimisticSetVisibility = "hide_once";
              render();
            })();
          },
        },
      });
      container.appendChild(setBtn);
    }
  };

  // Subscribe to store changes to re-render when POIs arrive
  const unsubscribe = subscribeBackendStore(() => render());
  setRefreshHandler?.(() => render());

  // Initial render
  render();

  return {
    root: container,
    dispose: () => {
      unsubscribe();
      if (postSelectTimer !== null) {
        globalThis.clearTimeout(postSelectTimer);
      }
    },
  };
}
