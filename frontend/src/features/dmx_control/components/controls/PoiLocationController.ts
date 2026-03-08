import { getBackendStore, subscribeBackendStore } from "../../../../shared/state/backend_state.ts";
import { setFixtureValues, updatePoiFixtureTarget } from "../../fixture_intents.ts";
import { Dropdown } from "../../../../shared/components/controls/Dropdown.ts";

export interface PoiLocationControllerOptions {
  fixtureId: string;
}

export function PoiLocationController({ fixtureId }: PoiLocationControllerOptions): HTMLElement {
  const container = document.createElement("div");
  container.className = "poi-controller-row";

  let currentSelectedPoiId = "";

  const render = () => {
    // Clear existing (except style)
    Array.from(container.children).forEach(child => {
      if (child.tagName !== "STYLE") container.removeChild(child);
    });

    const store = getBackendStore();
    const pois = store.state.pois || [];

    const dropdownWrap = document.createElement("div");
    dropdownWrap.className = "poi-dropdown-wrap";

    const options = pois.map(p => ({
      label: p.name,
      value: p.id
    }));

    if (options.length > 0 && !currentSelectedPoiId) {
        currentSelectedPoiId = options[0].value;
    }

    const dropdown = Dropdown({
      value: currentSelectedPoiId,
      options,
      onChange: (val) => {
        currentSelectedPoiId = val;
        
        const newPoi = pois.find(p => p.id === val) as any;
        const newFixData = newPoi?.fixtures?.[fixtureId];
        
        if (!newFixData) {
          // 1. Move to 0/0 if no data
          setFixtureValues(fixtureId, { pan: 0, tilt: 0 });
        } else {
          // 1. Move to the pan/tilt position
          setFixtureValues(fixtureId, { preset: val });
        }
      }
    });
    dropdownWrap.appendChild(dropdown);
    container.appendChild(dropdownWrap);

    // Evaluate visibility of "set" button
    const poi = pois.find(p => p.id === currentSelectedPoiId) as any;
    const fixtureDataInPoi = poi?.fixtures?.[fixtureId];
    const fixtureState = store.state.fixtures?.[fixtureId];
    const currentPan = Number(fixtureState?.values?.["pan"] ?? 0);
    const currentTilt = Number(fixtureState?.values?.["tilt"] ?? 0);

    let showSetBtn = false;
    if (!fixtureDataInPoi) {
      showSetBtn = true;
    } else {
      if (fixtureDataInPoi.pan !== currentPan || fixtureDataInPoi.tilt !== currentTilt) {
        showSetBtn = true;
      }
    }

    if (showSetBtn && currentSelectedPoiId) {
      const setBtn = document.createElement("button");
      setBtn.className = "poi-set-btn";
      setBtn.textContent = "set";
      setBtn.onclick = () => {
        updatePoiFixtureTarget(currentSelectedPoiId, fixtureId, currentPan, currentTilt);
      };
      container.appendChild(setBtn);
    }
  };

  // Subscribe to store changes to re-render when POIs arrive
  const unsubscribe = subscribeBackendStore(() => {
    render();
  });

  // Initial render
  render();

  return container;
}
