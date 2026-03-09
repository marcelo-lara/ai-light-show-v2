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
  onCommit?: (pan: number, tilt: number) => void;
}

export function PanTiltControl({
  fixtureId,
  initialPan = 128,
  initialTilt = 128,
  maxPan = 255,
  maxTilt = 255,
  onCommit,
}: PanTiltControlOptions): PanTiltControlHandle {
  const limits = { maxPan, maxTilt };
  const container = document.createElement("div");
  container.className = "pan-tilt-surface";

  const handle = document.createElement("div");
  handle.className = "pan-tilt-handle";
  container.appendChild(handle);

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
  let isDragging = false;
  let detachDragListeners: (() => void) | null = null;

  const updateHandle = () => {
    const position = handlePercent({ pan: currentPan, tilt: currentTilt }, limits);
    handle.style.left = position.left;
    handle.style.top = position.top;
    panLabel.textContent = `Pan ${Math.round(currentPan)}`;
    tiltLabel.textContent = `Tilt ${Math.round(currentTilt)}`;
  };

  const updateValues = (clientX: number, clientY: number) => {
    const point = pointFromPointer(container.getBoundingClientRect(), clientX, clientY, limits);
    currentPan = point.pan;
    currentTilt = point.tilt;
    updateHandle();
    sendUpdates(currentPan, currentTilt);
  };

  const sendUpdates = throttle((pan: number, tilt: number) => {
    setFixtureValues(fixtureId, { pan, tilt });
  }, 32);

  const beginDrag = (register: () => (() => void), firstX: number, firstY: number) => {
    isDragging = true;
    detachDragListeners = register();
    updateValues(firstX, firstY);
  };

  const handleMouseDown = (event: MouseEvent) => {
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

  container.addEventListener("mousedown", handleMouseDown);
  container.addEventListener("touchstart", handleTouchStart, { passive: false });

  const updatePanTilt = (pan: number, tilt: number) => {
    if (!isDragging) {
      currentPan = pan;
      currentTilt = tilt;
      updateHandle();
    }
  };

  const dispose = () => {
    container.removeEventListener("mousedown", handleMouseDown);
    container.removeEventListener("touchstart", handleTouchStart);
    if (detachDragListeners) {
      detachDragListeners();
      detachDragListeners = null;
    }
    isDragging = false;
  };

  updateHandle();

  return {
    root: container,
    updatePanTilt,
    dispose,
  };
}
