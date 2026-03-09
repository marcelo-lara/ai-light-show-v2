import { StandardControls } from "./StandardControls.ts";
import type { FixtureVM } from "../../adapters/fixture_vm.ts";
import { RgbPreview } from "./RgbPreview.ts";
import type { FixtureControlHandle, FixtureValues } from "./control_types.ts";

export function RgbControls(fixture: FixtureVM): FixtureControlHandle {
  const values = fixture.values;

  const wrap = document.createElement("div");
  wrap.className = "control-stack";

  // Specialized RGB Swatch/Preview
  const preview = RgbPreview({
    red: Number(values.red ?? 0),
    green: Number(values.green ?? 0),
    blue: Number(values.blue ?? 0),
    white: Number(values.white ?? 0),
  });
  wrap.appendChild(preview.root);

  // Use StandardControls for sliders/dropdowns
  const standard = StandardControls(fixture);
  wrap.appendChild(standard.root);

  const updateValues = (newValues: FixtureValues) => {
    preview.setRgb({
      red: Number(newValues.red ?? fixture.values.red ?? 0),
      green: Number(newValues.green ?? fixture.values.green ?? 0),
      blue: Number(newValues.blue ?? fixture.values.blue ?? 0),
      white: Number(newValues.white ?? fixture.values.white ?? 0),
    });
    standard.updateValues(newValues);
  };

  const dispose = () => {
    preview.dispose();
    standard.dispose();
  };

  return {
    root: wrap,
    updateValues,
    dispose,
  };
}
