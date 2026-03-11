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

type RgbPreviewOptions = {
  onColorChange?: (hex: string) => void;
};

function toByte(value: number): number {
  return Math.max(0, Math.min(255, Math.round(value)));
}

export function RgbPreview(initial: RgbPreviewState, options: RgbPreviewOptions = {}): RgbPreviewHandle {
  const root = document.createElement("div");
  root.className = "rgb-preview";

  const colorInput = document.createElement("input");
  colorInput.className = "rgb-preview-input";
  colorInput.type = "color";
  root.appendChild(colorInput);

  const label = document.createElement("div");
  label.className = "rgb-preview-label muted mono";
  root.appendChild(label);

  const toHex = (red: number, green: number, blue: number): string => {
    const r = toByte(red).toString(16).padStart(2, "0");
    const g = toByte(green).toString(16).padStart(2, "0");
    const b = toByte(blue).toString(16).padStart(2, "0");
    return `#${r}${g}${b}`;
  };

  const setRgb = (state: RgbPreviewState) => {
    const red = toByte(state.red);
    const green = toByte(state.green);
    const blue = toByte(state.blue);
    const white = toByte(state.white);

    const hex = toHex(red, green, blue);
    colorInput.value = hex;
    label.textContent = hex;
  };

  const emitColor = () => {
    options.onColorChange?.(colorInput.value.toUpperCase());
  };

  colorInput.addEventListener("input", emitColor);
  colorInput.addEventListener("change", emitColor);

  setRgb(initial);

  return {
    root,
    setRgb,
    dispose: () => {
      colorInput.removeEventListener("input", emitColor);
      colorInput.removeEventListener("change", emitColor);
    },
  };
}
