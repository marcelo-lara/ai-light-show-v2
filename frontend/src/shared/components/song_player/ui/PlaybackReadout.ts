export function PlaybackReadout(): {
  barBeatEl: HTMLElement;
  positionEl: HTMLElement;
} {
  const barBeatEl = document.createElement("div");
  barBeatEl.className = "song-player-barbeat mono";
  barBeatEl.textContent = "1.1";

  const positionEl = document.createElement("div");
  positionEl.className = "song-player-position mono muted";
  positionEl.textContent = "0:00 / 0:00";

  return { barBeatEl, positionEl };
}
