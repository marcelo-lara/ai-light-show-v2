import { throttle } from "../../../../shared/utils/throttle.ts";
import { setFixtureValues } from "../../fixture_intents.ts";
import { Slider } from "../../../../shared/components/controls/Slider.ts";
import { ColorSwatch } from "../../../../shared/components/controls/ColorSwatch.ts";
import { StandardControls } from "./StandardControls.ts";
import type { FixtureVM } from "../../adapters/fixture_vm.ts";

export function RgbControls(fixture: FixtureVM) {
  const fixtureId = fixture.id;
  const values = fixture.values;

  const wrap = document.createElement("div");
  wrap.className = "control-stack";

  // Specialized RGB Swatch/Preview
  const swatch = ColorSwatch({
    red: Number(values.red ?? 0),
    green: Number(values.green ?? 0),
    blue: Number(values.blue ?? 0),
    white: Number(values.white ?? 0),
  });
  wrap.appendChild(swatch);

  // Use StandardControls for sliders/dropdowns
  const standard = StandardControls(fixture);
  wrap.appendChild(standard);

  // Handle external updates
  (wrap as any).updateValues = (newValues: Record<string, number | string>) => {
    if (swatch && (swatch as any).setRgb) {
      (swatch as any).setRgb(
        Number(newValues.red ?? (fixture.values.red ?? 0)),
        Number(newValues.green ?? (fixture.values.green ?? 0)),
        Number(newValues.blue ?? (fixture.values.blue ?? 0)),
        Number(newValues.white ?? (fixture.values.white ?? 0))
      );
    }
    if ((standard as any).updateValues) {
      (standard as any).updateValues(newValues);
    }
  };

  return wrap;
}
