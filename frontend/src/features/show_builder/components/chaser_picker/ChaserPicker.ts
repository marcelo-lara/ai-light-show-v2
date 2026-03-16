import { Button } from "../../../../shared/components/controls/Button.ts";
import { Dropdown, type DropdownOption } from "../../../../shared/components/controls/Dropdown.ts";
import { Card } from "../../../../shared/components/layout/Card.ts";
import { subscribeBackendStore } from "../../../../shared/state/backend_state.ts";
import { applyChaser, startChaser } from "../../cue_intents.ts";
import { getChasers, getPlaybackTimeMs } from "../effect_picker/selectors.ts";

export function ChaserPicker(): HTMLElement {
	const body = document.createElement("div");
	body.className = "chaser-picker-body";

	let selected = "";
	let repetitions = "1";

	const chaserDropdown = Dropdown({
		label: "Chaser",
		value: "",
		options: [],
		onChange: (value) => {
			selected = value;
		},
	});
	chaserDropdown.root.classList.add("chaser-picker-field");

	const repsDropdown = Dropdown({
		label: "Repetitions",
		value: repetitions,
		options: Array.from({ length: 8 }, (_, i) => {
			const n = String(i + 1);
			return { value: n, label: n };
		}),
		onChange: (value) => {
			repetitions = value;
		},
	});
	repsDropdown.root.classList.add("chaser-picker-field", "chaser-picker-field--small");

	const actions = document.createElement("div");
	actions.className = "chaser-picker-actions";

	const applyBtn = Button({
		caption: "Apply",
		state: "primary",
		bindings: {
			onClick: () => {
				if (!selected) return;
				applyChaser(selected, getPlaybackTimeMs(), Number(repetitions));
			},
		},
	});

	const startBtn = Button({
		caption: "Start",
		bindings: {
			onClick: () => {
				if (!selected) return;
				startChaser(selected, getPlaybackTimeMs(), Number(repetitions));
			},
		},
	});

	actions.append(applyBtn, startBtn);

	const empty = document.createElement("p");
	empty.className = "chaser-picker-empty";
	empty.textContent = "No chasers available";

	function refresh() {
		const chasers = getChasers();
		const options: DropdownOption[] = chasers.map((chaser) => ({
			value: chaser.name,
			label: chaser.name,
		}));
		const nextValue = options.some((option) => option.value === selected) ? selected : (options[0]?.value ?? "");
		selected = nextValue;
		chaserDropdown.setOptions(options, nextValue);

		const disabled = options.length === 0;
		chaserDropdown.select.disabled = disabled;
		repsDropdown.select.disabled = disabled;
		applyBtn.disabled = disabled;
		startBtn.disabled = disabled;
		empty.style.display = disabled ? "block" : "none";
	}

	refresh();
	const unsubscribe = subscribeBackendStore(refresh);
	(body as unknown as { _cleanup: () => void })._cleanup = () => unsubscribe();

	body.append(chaserDropdown.root, repsDropdown.root, actions, empty);
	return Card(body, {
		title: "Chaser Picker",
		variant: "outlined",
		className: "show-builder-panel show-builder-flow-card",
	});
}
