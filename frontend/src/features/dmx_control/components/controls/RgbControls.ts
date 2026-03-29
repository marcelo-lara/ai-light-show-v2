import { StandardControls } from "./StandardControls.ts";
import type { FixtureVM } from "../../adapters/fixture_vm.ts";
import { ColorPicker } from "../../../../shared/components/controls/ColorPicker.ts";
import type { FixtureControlHandle, FixtureValues } from "./control_types.ts";
import { EnumGrid } from "./EnumGrid.ts";
import { setFixtureValues } from "../../fixture_intents.ts";

type RgbTriplet = { red: number; green: number; blue: number };
type ColorOption = { id: string; label: string; swatch: string; rgb: RgbTriplet; tokens: string[] };

function parseHexRgb(value: string): RgbTriplet | null {
  const clean = value.trim().replace(/^#/, "");
  if (!/^[0-9a-fA-F]{6}$/.test(clean)) return null;
  return {
    red: Number.parseInt(clean.slice(0, 2), 16),
    green: Number.parseInt(clean.slice(2, 4), 16),
    blue: Number.parseInt(clean.slice(4, 6), 16),
  };
}

function normalizeHex(value: string): string {
  return value.trim().replace(/^#/, "").toUpperCase();
}

function canonicalHex(value: string): string {
  return `#${normalizeHex(value)}`;
}

function normalizeToken(value: string): string {
  return value.trim().toLowerCase();
}

function rgbMappingOptions(rawMapping: Record<string, number | string>): ColorOption[] {
  const options: ColorOption[] = [];

  for (const [rawKey, rawValue] of Object.entries(rawMapping)) {
    const keyHex = parseHexRgb(rawKey);
    const valueStr = typeof rawValue === "string" ? rawValue : null;
    const valueHex = valueStr ? parseHexRgb(valueStr) : null;

    if (valueHex && valueStr) {
      const swatch = `#${normalizeHex(valueStr)}`;
      options.push({
        id: rawKey,
        label: rawKey,
        swatch,
        rgb: valueHex,
        tokens: [normalizeToken(rawKey), normalizeToken(normalizeHex(valueStr))],
      });
      continue;
    }

    if (keyHex && typeof rawValue === "string") {
      const swatch = `#${normalizeHex(rawKey)}`;
      options.push({
        id: rawValue,
        label: rawValue,
        swatch,
        rgb: keyHex,
        tokens: [normalizeToken(rawValue), normalizeToken(normalizeHex(rawKey))],
      });
    }
  }

  return options;
}

function colorIdFromRgb(options: ColorOption[], rgb: RgbTriplet): string {
  for (const option of options) {
    if (option.rgb.red === rgb.red && option.rgb.green === rgb.green && option.rgb.blue === rgb.blue) {
      return option.id;
    }
  }
  return "";
}

function colorIdFromToken(options: ColorOption[], token: unknown): string {
  if (typeof token !== "string") return "";
  const normalized = normalizeToken(token);
  for (const option of options) {
    if (option.tokens.includes(normalized)) {
      return option.id;
    }
  }
  return "";
}

export function RgbControls(fixture: FixtureVM): FixtureControlHandle {
  const values = fixture.values;
  const isParcan = fixture.type === "parcan";

  const wrap = document.createElement("div");
  wrap.className = "fixture-two-col";
  wrap.style.setProperty("--fixture-left-column-width", "var(--fixture-left-column-width-rgb, 108px)");

  const leftCol = document.createElement("div");
  leftCol.className = "fixture-two-col-left";

  const rightCol = document.createElement("div");
  rightCol.className = "fixture-two-col-right";

  const initialFromRgb = typeof values.rgb === "string" ? parseHexRgb(values.rgb) : null;
  const state = {
    red: Number(initialFromRgb?.red ?? values.red ?? 0),
    green: Number(initialFromRgb?.green ?? values.green ?? 0),
    blue: Number(initialFromRgb?.blue ?? values.blue ?? 0),
    white: Number(values.white ?? 0),
  };

  const colorPicker = ColorPicker({
    label: "Color",
    value: canonicalHex(`${state.red.toString(16).padStart(2, "0")}${state.green.toString(16).padStart(2, "0")}${state.blue.toString(16).padStart(2, "0")}`),
    onChange: (hex) => {
      setFixtureValues(fixture.id, { rgb: hex.toUpperCase() });
    },
  });
  leftCol.appendChild(colorPicker.root);

  let colorGridDispose = () => {};
  let colorGridSetValue: ((value: string) => void) | null = null;
  let colorOptions: ColorOption[] = [];
  let colorById: Record<string, ColorOption> = {};

  // Par cans expose an RGB meta channel with a backend-provided color mapping.
  if (isParcan) {
    const rgbMeta = fixture.metaChannels.rgb;
    const mappingId = rgbMeta?.kind === "rgb" ? rgbMeta.mapping : undefined;
    const rawMapping = mappingId ? fixture.mappings[mappingId] ?? {} : {};
    colorOptions = rgbMappingOptions(rawMapping);
    colorById = Object.fromEntries(colorOptions.map((option) => [option.id, option]));

    const options = colorOptions.map((option) => ({
      label: option.label,
      value: option.id,
      swatch: option.swatch,
    }));

    if (options.length > 0) {
      const initialColor = colorIdFromToken(colorOptions, values.rgb) || colorIdFromRgb(colorOptions, state);
      const grid = EnumGrid({
        label: "Color",
        value: initialColor,
        options,
        onChange: (id) => {
          const mapped = colorById[id];
          if (!mapped) return;
          setFixtureValues(fixture.id, {
            rgb: canonicalHex(mapped.swatch),
          });
        },
      });
      colorGridSetValue = grid.setValue;
      colorGridDispose = grid.dispose;
      leftCol.appendChild(grid.root);
    }
  }

  // Use StandardControls for sliders/dropdowns
  const standard = StandardControls(fixture);
  rightCol.appendChild(standard.root);
  wrap.append(leftCol, rightCol);

  const updateValues = (newValues: FixtureValues) => {
    const parsedRgb = typeof newValues.rgb === "string" ? parseHexRgb(newValues.rgb) : null;
    if (parsedRgb) {
      state.red = parsedRgb.red;
      state.green = parsedRgb.green;
      state.blue = parsedRgb.blue;
    }

    const colorFromToken = colorIdFromToken(colorOptions, newValues.rgb);
    if (colorFromToken) {
      const mapped = colorById[colorFromToken];
      if (mapped) {
        state.red = mapped.rgb.red;
        state.green = mapped.rgb.green;
        state.blue = mapped.rgb.blue;
      }
    }

    state.red = Number(newValues.red ?? state.red);
    state.green = Number(newValues.green ?? state.green);
    state.blue = Number(newValues.blue ?? state.blue);
    state.white = Number(newValues.white ?? state.white);

    colorPicker.setValue(canonicalHex(`${state.red.toString(16).padStart(2, "0")}${state.green.toString(16).padStart(2, "0")}${state.blue.toString(16).padStart(2, "0")}`));

    if (colorGridSetValue) {
      const selectedColor = colorIdFromToken(colorOptions, newValues.rgb) || colorIdFromRgb(colorOptions, state);
      colorGridSetValue(selectedColor);
    }

    standard.updateValues(newValues);
  };

  const dispose = () => {
    colorPicker.dispose();
    colorGridDispose();
    standard.dispose();
  };

  return {
    root: wrap,
    updateValues,
    dispose,
  };
}
