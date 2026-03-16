import { createSvgIcon } from "../../../utils/svg.ts";
import { ICON_REGISTRY } from "../../../svg_icons/index.ts";

export function TransportControls(callbacks: {
  onPrevSection: () => void;
  onPrevBeat: () => void;
  onStop: () => void;
  onPlayPause: () => void;
  onNextBeat: () => void;
  onNextSection: () => void;
}): {
  container: HTMLElement;
  prevSectionBtn: HTMLButtonElement;
  prevBeatBtn: HTMLButtonElement;
  stopBtn: HTMLButtonElement;
  playPauseBtn: HTMLButtonElement;
  nextBeatBtn: HTMLButtonElement;
  nextSectionBtn: HTMLButtonElement;
  updatePlayPauseIcon: (playing: boolean) => void;
} {
  const container = document.createElement("div");
  container.className = "song-player-transport";

  const btn = (label: string, iconName: string, onClick: () => void, className = "btn") => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = className;
    b.title = label;
    b.setAttribute("aria-label", label);
    
    // @ts-ignore: index access
    const paths = ICON_REGISTRY[iconName];
    if (paths) {
      b.appendChild(createSvgIcon(paths, "transport-icon"));
    } else {
      b.textContent = label;
    }

    b.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      onClick();
    });
    return b;
  };

  const prevSectionBtn = btn("Prev Section", "playerPrev", callbacks.onPrevSection);
  const prevBeatBtn = btn("Prev Beat", "playerPrev", callbacks.onPrevBeat);
  const stopBtn = btn("Stop", "playerStop", callbacks.onStop);
  const playPauseBtn = btn("Play", "playerPlay", callbacks.onPlayPause, "btn play-pause-btn");
  const nextBeatBtn = btn("Next Beat", "playerNext", callbacks.onNextBeat);
  const nextSectionBtn = btn("Next Section", "playerNext", callbacks.onNextSection);

  const updatePlayPauseIcon = (playing: boolean) => {
    const iconName = playing ? "playerPause" : "playerPlay";
    const label = playing ? "Pause" : "Play";
    playPauseBtn.title = label;
    playPauseBtn.setAttribute("aria-label", label);
    playPauseBtn.innerHTML = "";
    const paths = ICON_REGISTRY[iconName];
    playPauseBtn.appendChild(createSvgIcon(paths, "transport-icon"));
  };

  container.append(
    prevSectionBtn,
    prevBeatBtn,
    stopBtn,
    playPauseBtn,
    nextBeatBtn,
    nextSectionBtn
  );

  return {
    container,
    prevSectionBtn,
    prevBeatBtn,
    stopBtn,
    playPauseBtn,
    nextBeatBtn,
    nextSectionBtn,
    updatePlayPauseIcon,
  };
}
