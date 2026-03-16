import { Slider } from "../../controls/Slider.ts";

export function PlayerOptions(callbacks: {
  onLoopToggle: (checked: boolean) => void;
  onShowSectionsToggle: (checked: boolean) => void;
  onShowDownbeatsToggle: (checked: boolean) => void;
}): {
  container: HTMLElement;
  loopToggle: HTMLInputElement;
  showSectionsToggle: HTMLInputElement;
  showDownbeatsToggle: HTMLInputElement;
} {
  const container = document.createElement("div");
  container.className = "song-player-options";

  const toggle = (label: string, checked: boolean, onChange: (val: boolean) => void) => {
    const l = document.createElement("label");
    l.className = "song-player-inline-toggle";
    const i = document.createElement("input");
    i.type = "checkbox";
    i.checked = checked;
    i.addEventListener("change", () => onChange(i.checked));
    const s = document.createElement("span");
    s.textContent = label;
    l.append(i, s);
    return { labelEl: l, inputEl: i };
  };

  const loop = toggle("Loop Regions", false, callbacks.onLoopToggle);
  const showSections = toggle("Sections", false, callbacks.onShowSectionsToggle);
  const showDownbeats = toggle("Downbeats", true, callbacks.onShowDownbeatsToggle);

  container.append(loop.labelEl, showSections.labelEl, showDownbeats.labelEl);

  return {
    container,
    loopToggle: loop.inputEl,
    showSectionsToggle: showSections.inputEl,
    showDownbeatsToggle: showDownbeats.inputEl,
  };
}

export function ZoomControl(opts: {
  initialZoom: number;
  onZoom: (val: number) => void;
}): {
  container: HTMLElement;
  zoomSlider: HTMLInputElement;
  dispose: () => void;
} {
  const container = document.createElement("div");
  container.className = "song-player-zoom-container";

  const zoom = Slider({
    label: "zoom",
    min: 1,
    max: 180,
    step: 5,
    value: opts.initialZoom,
    onInput: opts.onZoom,
    className: "song-player-zoom",
  });

  container.appendChild(zoom.root);

  return {
    container,
    zoomSlider: zoom.input,
    dispose: zoom.dispose,
  };
}
