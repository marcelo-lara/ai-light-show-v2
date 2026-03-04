export function Layout(parts: {
  waveform: HTMLElement;
  barBeat: HTMLElement;
  transport: HTMLElement;
  options: HTMLElement;
  zoom: HTMLElement;
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
  const colBarBeat = document.createElement("div");
  colBarBeat.className = "song-player-col-barbeat";
  colBarBeat.append(parts.barBeat);

  // Column 2: Transport
  const colTransport = document.createElement("div");
  colTransport.className = "song-player-col-transport";
  colTransport.append(parts.transport);

  // Column 3: Options
  const colOptions = document.createElement("div");
  colOptions.className = "song-player-col-options";
  colOptions.append(parts.options);

  // Column 4: Zoom
  const colZoom = document.createElement("div");
  colZoom.className = "song-player-col-zoom";
  colZoom.append(parts.zoom);

  // Column 5: Position
  const colPosition = document.createElement("div");
  colPosition.className = "song-player-col-position";
  colPosition.append(parts.position);

  row2.append(colBarBeat, colTransport, colOptions, colPosition, colZoom);

  root.append(row1, row2);
  return root;
}
