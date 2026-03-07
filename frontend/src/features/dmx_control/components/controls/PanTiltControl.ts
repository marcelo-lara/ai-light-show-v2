import { throttle } from "../../../../shared/utils/throttle.ts";
import { setFixtureValues } from "../../fixture_intents.ts";

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
}: PanTiltControlOptions): HTMLElement {
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

  const updateHandle = () => {
    handle.style.left = `${(currentPan / maxPan) * 100}%`;
    handle.style.top = `${(currentTilt / maxTilt) * 100}%`;
  };

  const updateValues = (clientX: number, clientY: number) => {
    const rect = container.getBoundingClientRect();
    const x = Math.max(0, Math.min(rect.width, clientX - rect.left));
    const y = Math.max(0, Math.min(rect.height, clientY - rect.top));
    
    currentPan = Math.round((x / rect.width) * maxPan);
    currentTilt = Math.round((y / rect.height) * maxTilt);
    
    updateHandle();
    sendUpdates(currentPan, currentTilt);
  };

  const sendUpdates = throttle((pan: number, tilt: number) => {
    setFixtureValues(fixtureId, { pan, tilt });
  }, 32);

  const handleMouseDown = (e: MouseEvent) => {
    isDragging = true;
    const onMouseMove = (moveEv: MouseEvent) => {
      updateValues(moveEv.clientX, moveEv.clientY);
    };
    const onMouseUp = () => {
      isDragging = false;
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
      if (onCommit) onCommit(currentPan, currentTilt);
    };
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    updateValues(e.clientX, e.clientY);
  };

  const handleTouchStart = (e: TouchEvent) => {
    isDragging = true;
    const onTouchMove = (moveEv: TouchEvent) => {
      if (moveEv.touches.length > 0) {
        updateValues(moveEv.touches[0].clientX, moveEv.touches[0].clientY);
      }
    };
    const onTouchEnd = () => {
      isDragging = false;
      window.removeEventListener("touchmove", onTouchMove);
      window.removeEventListener("touchend", onTouchEnd);
      if (onCommit) onCommit(currentPan, currentTilt);
    };
    window.addEventListener("touchmove", onTouchMove);
    window.addEventListener("touchend", onTouchEnd);
    if (e.touches.length > 0) {
      updateValues(e.touches[0].clientX, e.touches[0].clientY);
    }
  };

  container.addEventListener("mousedown", handleMouseDown);
  container.addEventListener("touchstart", handleTouchStart, { passive: false });

  // Expose methods for external updates
  (container as any).updatePanTilt = (pan: number, tilt: number) => {
    if (!isDragging) {
      currentPan = pan;
      currentTilt = tilt;
      updateHandle();
    }
  };

  updateHandle();

  return container;
}
