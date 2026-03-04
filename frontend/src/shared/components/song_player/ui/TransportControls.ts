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
} {
  const container = document.createElement("div");
  container.className = "song-player-transport";

  const btn = (label: string, onClick: () => void) => {
    const b = document.createElement("button");
    b.className = "btn";
    b.textContent = label;
    b.addEventListener("click", onClick);
    return b;
  };

  const prevSectionBtn = btn("Prev Section", callbacks.onPrevSection);
  const prevBeatBtn = btn("Prev Beat", callbacks.onPrevBeat);
  const stopBtn = btn("Stop", callbacks.onStop);
  const playPauseBtn = btn("Play", callbacks.onPlayPause);
  const nextBeatBtn = btn("Next Beat", callbacks.onNextBeat);
  const nextSectionBtn = btn("Next Section", callbacks.onNextSection);

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
  };
}
