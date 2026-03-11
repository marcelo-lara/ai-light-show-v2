export function Waveform(): { container: HTMLElement; wave: HTMLElement; title: HTMLElement } {
  const container = document.createElement("div");
  container.className = "song-player-waveform";

  const title = document.createElement("div");
  title.className = "song-player-title muted";
  title.textContent = "No song loaded";

  const wave = document.createElement("div");
  wave.className = "song-player-wave";

  container.append(title, wave);

  return { container, wave, title };
}
