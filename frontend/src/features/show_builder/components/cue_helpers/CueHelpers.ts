import { Card } from "../../../../shared/components/layout/Card.ts";
import { Button } from "../../../../shared/components/controls/Button.ts";
import { Dropdown } from "../../../../shared/components/controls/Dropdown.ts";
import { subscribeBackendStore } from "../../../../shared/state/backend_state.ts";
import type { CueHelperDefinition } from "../../../../shared/transport/protocol.ts";
import { getCueHelpers } from "../effect_picker/selectors.ts";
import { getPlaybackTimeMs } from "../effect_picker/selectors.ts";
import { applyCueHelper } from "../../cue_intents.ts";
import { CueHelperParamForm } from "./CueHelperParamForm.ts";
import { hydrateCueHelperParams } from "./defaults.ts";

export function CueHelpers(): HTMLElement {
	const content = document.createElement("div");
	content.className = "cue-helpers";
	const state: { helperId: string; params: Record<string, unknown> } = {
		helperId: "",
		params: {},
	};

	function getSelectedHelper(helpers: CueHelperDefinition[]): CueHelperDefinition | undefined {
		return helpers.find((helper) => helper.id === state.helperId) ?? helpers[0];
	}

	function syncSelection(helpers: CueHelperDefinition[]) {
		const selected = getSelectedHelper(helpers);
		if (!selected) {
			state.helperId = "";
			state.params = {};
			return;
		}

		const shouldReset = selected.id !== state.helperId;
		state.helperId = selected.id;
		state.params = hydrateCueHelperParams(
			selected,
			shouldReset ? {} : state.params,
			getPlaybackTimeMs(),
		);
	}

	function render() {
		content.innerHTML = "";
		const helpers = getCueHelpers();
		syncSelection(helpers);

		if (helpers.length === 0) {
			const empty = document.createElement("p");
			empty.className = "cue-helper-empty";
			empty.textContent = "No cue helpers available.";
			content.appendChild(empty);
			return;
		}

		const helper = getSelectedHelper(helpers);
		if (!helper) {
			return;
		}

		const dropdown = Dropdown({
			value: helper.id,
			options: helpers.map((item) => ({ value: item.id, label: item.label })),
			onChange: (value) => {
				state.helperId = value;
				state.params = {};
				render();
			},
		});

		const header = document.createElement("div");
		header.className = "cue-helper-header";

		const label = document.createElement("div");
		label.className = "cue-helper-label";
		label.textContent = helper.label;

		const description = document.createElement("div");
		description.className = "cue-helper-description";
		description.textContent = helper.description;

		header.append(label, description);

		const form = CueHelperParamForm({
			helper,
			values: state.params,
			onChange: (name, value) => {
				state.params[name] = value;
			},
		});

		const actions = document.createElement("div");
		actions.className = "cue-helper-actions";
		actions.appendChild(Button({
			caption: "Apply",
			state: "primary",
			bindings: {
				onClick: () => applyCueHelper(helper.id, state.params),
			},
		}));

		content.append(dropdown.root, header, form, actions);
	}

	render();
	const unsubscribe = subscribeBackendStore(render);
	(content as unknown as { _cleanup: () => void })._cleanup = unsubscribe;

	return Card(content, {
		variant: "outlined",
		className: "show-builder-panel",
	});
}