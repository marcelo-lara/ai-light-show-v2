import { getBackendStore, subscribeBackendStore } from "../../../../shared/state/backend_state.ts";
import { setFixtureValues } from "../../fixture_intents.ts";
import { Dropdown } from "../../../../shared/components/controls/Dropdown.ts";

export interface PoiLocationControllerOptions {
  fixtureId: string;
}

export function PoiLocationController({ fixtureId }: PoiLocationControllerOptions): HTMLElement {
  const container = document.createElement("div");
  container.className = "poi-controller-row";

  // Basic styling for the row
  const style = document.createElement("style");
  style.textContent = `
    .poi-controller-row {
      display: flex;
      align-items: flex-end;
      gap: 8px;
      margin-top: 10px;
      padding: 0 4px;
    }
    .poi-dropdown-wrap {
      flex: 1;
    }
    .poi-set-btn {
      background: var(--surface-low, #1e1e1e);
      border: 1px solid var(--border-color, #333);
      color: var(--text-color, #fff);
      padding: 8px 16px;
      height: 38px; /* Match dropdown height roughly */
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
      transition: background 0.2s, border-color 0.2s;
    }
    .poi-set-btn:hover {
      background: var(--surface-mid, #2a2a2a);
      border-color: var(--accent-color, #007acc);
    }
    .poi-set-btn:active {
      transform: translateY(1px);
    }
  `;
  container.appendChild(style);

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
      label: "Go to POI",
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
