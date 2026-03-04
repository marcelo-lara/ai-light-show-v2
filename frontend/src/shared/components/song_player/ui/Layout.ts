export function Layout(parts: {
  waveform: HTMLElement;
  barBeat: HTMLElement;
  transport: HTMLElement;
  options: HTMLElement;
  position: HTMLElement;
}): HTMLElement {
  const root = document.createElement("section");
  root.className = "card song-player-v2";

  // First row: Waveform
  const row1 = document.createElement("div");
  row1.className = "song-player-row-1";
  row1.append(parts.waveform);

  // Second row: Controls in columns
  const row2 = document.createElement("div");
  row2.className = "song-player-row-2";
  
  // Column 1: Bar.Beat
  const col1 = document.createElement("div");
  col1.className = "song-player-col-barbeat";
  col1.append(parts.barBeat);

  // Column 2: Transport
  const col2 = document.createElement("div");
  col2.className = "song-player-col-transport";
  col2.append(parts.transport);

  // Column 3: Options
  const col3 = document.createElement("div");
  col3.className = "song-player-col-options";
  col3.append(parts.options);

  // Column 4: Position (shared column with zoom in mockup usually, but here we separate)
  const col4 = document.createElement("div");
  col4.className = "song-player-col-position";
  col4.append(parts.position);

  row2.append(col1, col2, col3, col4);

  root.append(row1, row2);
  return root;
}
