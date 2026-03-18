import { ChaserPicker } from "../chaser_picker/ChaserPicker.ts";
import { EffectPicker } from "../effect_picker/EffectPicker.ts";
import { CueHelpers } from "../cue_helpers/CueHelpers.ts";

export function FlowColumn(): HTMLElement {
	const col = document.createElement("div");
	col.className = "show-builder-flow-column";
	col.append(
		EffectPicker(),
		ChaserPicker(),
		CueHelpers(),
	);
	return col;
}
