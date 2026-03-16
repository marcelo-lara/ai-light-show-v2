import { Card } from "../../../../shared/components/layout/Card.ts";
import { EffectPicker } from "../effect_picker/EffectPicker.ts";
import { CueHelpers } from "../cue_helpers/CueHelpers.ts";

function EmptyFlowCard(title: string): HTMLElement {
	const content = document.createElement("div");
	content.className = "show-builder-flow-empty";
	return Card(content, {
		title,
		variant: "outlined",
		className: "show-builder-panel show-builder-flow-card",
	});
}

export function FlowColumn(): HTMLElement {
	const col = document.createElement("div");
	col.className = "show-builder-flow-column";
	col.append(
		EffectPicker(),
		EmptyFlowCard("ChaserPicker"),
		CueHelpers(),
	);
	return col;
}
