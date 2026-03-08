import { getBackendStore, subscribeBackendStore } from "../../../../shared/state/backend_state.ts";
import { setFixtureValues } from "../../fixture_intents.ts";
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
        // Optional: auto-move on change or wait for 'set' button?
        // Mockup shows a 'set' button, so we'll just update the local state.
      }
    });
    dropdownWrap.appendChild(dropdown);
    container.appendChild(dropdownWrap);

    const setBtn = document.createElement("button");
    setBtn.className = "poi-set-btn";
    setBtn.textContent = "set";
    setBtn.onclick = () => {
      if (currentSelectedPoiId) {
        setFixtureValues(fixtureId, { preset: currentSelectedPoiId });
      }
    };
    container.appendChild(setBtn);
  };

  // Subscribe to store changes to re-render when POIs arrive
  const unsubscribe = subscribeBackendStore(() => {
    render();
  });

  // Initial render
  render();

  return container;
}
