import { getBackendStore, subscribeBackendStore } from "../../../../shared/state/backend_state.ts";
import { setFixtureValues } from "../../fixture_intents.ts";

export interface PoiLocationControllerOptions {
  fixtureId: string;
}

export function PoiLocationController({ fixtureId }: PoiLocationControllerOptions): HTMLElement {
  const container = document.createElement("div");
  container.className = "poi-grid";

  // Basic styling for the grid
  const style = document.createElement("style");
  style.textContent = `
    .poi-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
      margin-top: 10px;
    }
    .poi-btn {
      background: var(--surface-low, #1e1e1e);
      border: 1px solid var(--border-color, #333);
      color: var(--text-color, #fff);
      padding: 12px 8px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
      transition: background 0.2s, border-color 0.2s;
      text-align: center;
    }
    .poi-btn:hover {
      background: var(--surface-mid, #2a2a2a);
      border-color: var(--accent-color, #007acc);
    }
    .poi-btn:active {
      transform: translateY(1px);
    }
  `;
  container.appendChild(style);

  const renderButtons = () => {
    // Clear existing buttons (except style)
    Array.from(container.children).forEach(child => {
      if (child.tagName !== "STYLE") container.removeChild(child);
    });

    const store = getBackendStore();
    const pois = store.state.pois || [];

    if (pois.length === 0) {
      const placeholder = document.createElement("div");
      placeholder.textContent = "No POIs loaded";
      placeholder.style.gridColumn = "span 2";
      placeholder.style.color = "rgba(255,255,255,0.3)";
      placeholder.style.textAlign = "center";
      placeholder.style.padding = "10px";
      container.appendChild(placeholder);
      return;
    }

    for (const poi of pois) {
      const btn = document.createElement("button");
      btn.className = "poi-btn";
      btn.textContent = poi.name;
      btn.onclick = () => {
        // Send the POI ID to the backend as a 'preset' instead of raw coordinates.
        // The backend knows the precise 16-bit Pan/Tilt values for each POI.
        setFixtureValues(fixtureId, { preset: poi.id });
      };
      container.appendChild(btn);
    }
  };

  // Subscribe to store changes to re-render buttons when POIs arrive
  const unsubscribe = subscribeBackendStore(() => {
    renderButtons();
  });

  // Initial render
  renderButtons();

  // Cleanup subscription if container is ever removed (manual cleanup needed in this vanilla setup)
  // In a more robust setup, we'd use a life-cycle hook.
  
  return container;
}
