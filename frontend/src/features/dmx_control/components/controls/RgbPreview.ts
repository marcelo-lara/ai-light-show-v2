export type RgbPreviewState = {
  red: number;
  green: number;
  blue: number;
  white: number;
};

export type RgbPreviewHandle = {
  root: HTMLElement;
  setRgb: (state: RgbPreviewState) => void;
  dispose: () => void;
};

function toByte(value: number): number {
  return Math.max(0, Math.min(255, Math.round(value)));
}

export function RgbPreview(initial: RgbPreviewState): RgbPreviewHandle {
  const root = document.createElement("div");
  root.className = "rgb-preview";

  const swatch = document.createElement("div");
  swatch.className = "rgb-preview-swatch";
  root.appendChild(swatch);

  const label = document.createElement("div");
  label.className = "rgb-preview-label muted mono";
  root.appendChild(label);

  const setRgb = (state: RgbPreviewState) => {
    const red = toByte(state.red);
    const green = toByte(state.green);
    const blue = toByte(state.blue);
    const white = toByte(state.white);

    const whiteMix = white / 255;
    const mixedRed = toByte(red + ((255 - red) * whiteMix));
    const mixedGreen = toByte(green + ((255 - green) * whiteMix));
    const mixedBlue = toByte(blue + ((255 - blue) * whiteMix));

    swatch.style.background = `rgb(${mixedRed}, ${mixedGreen}, ${mixedBlue})`;
    label.textContent = `R:${red} G:${green} B:${blue} W:${white}`;
  };

  setRgb(initial);

  return {
    root,
    setRgb,
    dispose: () => {},
  };
}
