import { Card } from "../../../../shared/components/layout/Card.ts";
import { Button } from "../../../../shared/components/controls/Button.ts";
import { getCueHelpers } from "../effect_picker/selectors.ts";
import { applyCueHelper } from "../../cue_intents.ts";

export function CueHelpers(): HTMLElement {
	const content = document.createElement("div");
	content.className = "cue-helpers";

	function render() {
		content.innerHTML = "";
		const helpers = getCueHelpers();

		if (helpers.length === 0) {
			content.textContent = "No cue helpers available";
			return;
		}

		for (const helper of helpers) {
			const helperDiv = document.createElement("div");
			helperDiv.className = "cue-helper-item";

			const label = document.createElement("div");
			label.className = "cue-helper-label";
			label.textContent = helper.label;

			const description = document.createElement("div");
			description.className = "cue-helper-description";
			description.textContent = helper.description;

			const button = Button({
				caption: "Apply",
				state: "primary",
				bindings: {
					onClick: () => applyCueHelper(helper.id),
				},
			});

			helperDiv.append(label, description, button);
			content.append(helperDiv);
		}
	}

	// Initial render
	render();

	// Re-render when backend state changes
	const unsubscribe = window.addEventListener("backend-state-update", render);
	// Note: In a real implementation, we'd use the proper subscription mechanism

	return Card(content, {
		title: "Cue Helpers",
		variant: "outlined",
		className: "show-builder-panel",
	});
}