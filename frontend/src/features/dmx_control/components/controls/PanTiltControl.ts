import { throttle } from "../../../../shared/utils/throttle.ts";
import { setFixtureValues } from "../../fixture_intents.ts";
import type { PanTiltControlHandle } from "./control_types.ts";
import { handlePercent, pointFromPointer } from "./pan_tilt_math.ts";
import { startMouseDrag, startTouchDrag } from "./pan_tilt_drag.ts";

export interface PanTiltControlOptions {
  fixtureId: string;
  initialPan?: number;
  initialTilt?: number;
  maxPan?: number;
  maxTilt?: number;
  poiPan?: number | null;
  poiTilt?: number | null;
  onChange?: (pan: number, tilt: number) => void;
  onCommit?: (pan: number, tilt: number) => void;
}

export function PanTiltControl({
  fixtureId,
  initialPan = 128,
  initialTilt = 128,
  maxPan = 255,
  maxTilt = 255,
  poiPan = null,
  poiTilt = null,
  onChange,
  onCommit,
}: PanTiltControlOptions): PanTiltControlHandle {
  const limits = { maxPan, maxTilt };
  const container = document.createElement("div");
  container.className = "pan-tilt-surface";
  container.tabIndex = 0;
  container.setAttribute("aria-label", `Pan and tilt control for ${fixtureId}`);

  const handle = document.createElement("div");
  handle.className = "pan-tilt-handle";
  container.appendChild(handle);

  const poiHandle = document.createElement("div");
  poiHandle.className = "pan-tilt-handle poi";
  container.appendChild(poiHandle);

  const panLabel = document.createElement("div");
  panLabel.className = "pan-tilt-label pan";
  panLabel.textContent = "Pan";
  container.appendChild(panLabel);

  const tiltLabel = document.createElement("div");
  tiltLabel.className = "pan-tilt-label tilt";
  tiltLabel.textContent = "Tilt";
  container.appendChild(tiltLabel);

  let currentPan = initialPan;
  let currentTilt = initialTilt;
  let currentPoiPan: number | null = poiPan;
  let currentPoiTilt: number | null = poiTilt;
  let isDragging = false;
  let isActive = false;
  let detachDragListeners: (() => void) | null = null;

  const clamp = (value: number, maxValue: number) => Math.max(0, Math.min(maxValue, value));

  const updatePoiHandle = () => {
    if (currentPoiPan === null || currentPoiTilt === null) {
      poiHandle.style.display = "none";
      return;
    }
    const position = handlePercent({ pan: currentPoiPan, tilt: currentPoiTilt }, limits);
    poiHandle.style.left = position.left;
    poiHandle.style.top = position.top;
    poiHandle.style.display = "block";
  };

  const updateHandle = () => {
    const position = handlePercent({ pan: currentPan, tilt: currentTilt }, limits);
    handle.style.left = position.left;
    handle.style.top = position.top;
    panLabel.textContent = `Pan ${Math.round(currentPan)}`;
    tiltLabel.textContent = `Tilt ${Math.round(currentTilt)}`;
  };

  const applyValues = (pan: number, tilt: number) => {
    currentPan = clamp(pan, maxPan);
    currentTilt = clamp(tilt, maxTilt);
    updateHandle();
    onChange?.(currentPan, currentTilt);
  };

  const updateValues = (clientX: number, clientY: number) => {
    const point = pointFromPointer(container.getBoundingClientRect(), clientX, clientY, limits);
    applyValues(point.pan, point.tilt);
    sendUpdates(currentPan, currentTilt);
  };

  const stepValues = (panDelta: number, tiltDelta: number) => {
    applyValues(currentPan + panDelta, currentTilt + tiltDelta);
    setFixtureValues(fixtureId, { pan: currentPan, tilt: currentTilt });
  };

  const sendUpdates = throttle((pan: number, tilt: number) => {
    setFixtureValues(fixtureId, { pan, tilt });
  }, 32);

  const beginDrag = (register: () => (() => void), firstX: number, firstY: number) => {
    isDragging = true;
    detachDragListeners = register();
    updateValues(firstX, firstY);
  };

  const activate = () => {
    if (isActive) return;
    isActive = true;
    container.classList.add("is-active");
    container.focus();
    document.dispatchEvent(new CustomEvent("pan-tilt-surface-activated", { detail: container }));
  };

  const deactivate = () => {
    if (!isActive) return;
    isActive = false;
    container.classList.remove("is-active");
  };

  const handleMouseDown = (event: MouseEvent) => {
    activate();
    beginDrag(
      () =>
        startMouseDrag({
          onMove: (clientX, clientY) => updateValues(clientX, clientY),
          onEnd: () => {
            isDragging = false;
            detachDragListeners = null;
            if (onCommit) onCommit(currentPan, currentTilt);
          },
        }),
      event.clientX,
      event.clientY,
    );
  };

  const handleTouchStart = (event: TouchEvent) => {
    if (event.touches.length === 0) return;
    activate();
    beginDrag(
      () =>
        startTouchDrag({
          onMove: (clientX, clientY) => updateValues(clientX, clientY),
          onEnd: () => {
            isDragging = false;
            detachDragListeners = null;
            if (onCommit) onCommit(currentPan, currentTilt);
          },
        }),
      event.touches[0].clientX,
      event.touches[0].clientY,
    );
  };

  const handleKeyDown = (event: KeyboardEvent) => {
    if (isDragging || !isActive) return;

    const step = event.shiftKey ? 128 : 1;

    switch (event.key) {
      case "ArrowUp":
        event.preventDefault();
        stepValues(0, step);
        break;
      case "ArrowDown":
        event.preventDefault();
        stepValues(0, -step);
        break;
      case "ArrowLeft":
        event.preventDefault();
        stepValues(step, 0);
        break;
      case "ArrowRight":
        event.preventDefault();
        stepValues(-step, 0);
        break;
      case "Escape":
        deactivate();
        break;
      default:
        break;
    }
  };

  const handleDocumentPointerDown = (event: PointerEvent) => {
    if (!isActive) return;
    if (event.target instanceof Node && container.contains(event.target)) return;
    deactivate();
  };

  const handleSurfaceActivated = (event: Event) => {
    const activatedContainer = (event as CustomEvent<HTMLElement>).detail;
    if (activatedContainer !== container) {
      deactivate();
    }
  };

  container.addEventListener("mousedown", handleMouseDown);
  container.addEventListener("touchstart", handleTouchStart, { passive: false });
  window.addEventListener("keydown", handleKeyDown);
  document.addEventListener("pointerdown", handleDocumentPointerDown);
  document.addEventListener("pan-tilt-surface-activated", handleSurfaceActivated);

  const updatePanTilt = (pan: number, tilt: number) => {
    applyValues(pan, tilt);
  };

  const dispose = () => {
    container.removeEventListener("mousedown", handleMouseDown);
    container.removeEventListener("touchstart", handleTouchStart);
    window.removeEventListener("keydown", handleKeyDown);
    document.removeEventListener("pointerdown", handleDocumentPointerDown);
    document.removeEventListener("pan-tilt-surface-activated", handleSurfaceActivated);
    if (detachDragListeners) {
      detachDragListeners();
      detachDragListeners = null;
    }
    isDragging = false;
    isActive = false;
  };

  updateHandle();
  updatePoiHandle();

  return {
    root: container,
    activate,
    updatePanTilt,
    updatePoiTarget: (pan, tilt) => {
      currentPoiPan = pan;
      currentPoiTilt = tilt;
      updatePoiHandle();
    },
    dispose,
  };
}
