import { Button } from "../../../../shared/components/controls/Button.ts";
import { Dropdown, type DropdownControl } from "../../../../shared/components/controls/Dropdown.ts";
import { Input, type InputControl } from "../../../../shared/components/controls/Input.ts";
import { time_position } from "../time_position.ts";

export type TopRowRefs = {
	root: HTMLElement;
	timeInput: HTMLInputElement;
	fixtureDropdown: DropdownControl;
	effectDropdown: DropdownControl;
};

export type MiddleRefs = {
	root: HTMLElement;
	durationInput: InputControl;
	paramFormContainer: HTMLElement;
};

export type ActionRefs = {
	root: HTMLElement;
	commitBtn: HTMLButtonElement;
	cancelBtn: HTMLButtonElement;
	previewBtn: HTMLButtonElement;
};

export function createDivider(): HTMLElement {
	const d = document.createElement("div");
	d.className = "effect-picker-divider";
	d.setAttribute("aria-hidden", "true");
	return d;
}

function field(cls: string): HTMLElement {
	const el = document.createElement("div");
	el.className = `effect-picker-field ${cls}`;
	return el;
}

export function buildTopRow(timeValue: string): TopRowRefs {
	const root = document.createElement("div");
	root.className = "effect-picker-top";
	const tc = time_position(timeValue, "Current playback time");
	tc.root.classList.add("effect-picker-field", "time_position-field");
	const fixtureField = field("effect-picker-field-grow");
	const fixtureDropdown = Dropdown({
		value: "",
		options: [],
		attributes: { "aria-label": "Fixture" },
	});
	fixtureField.appendChild(fixtureDropdown.root);
	const effectField = field("effect-picker-field-grow");
	const effectDropdown = Dropdown({
		value: "",
		options: [],
		attributes: { "aria-label": "Effect" },
	});
	effectField.appendChild(effectDropdown.root);
	root.append(tc.root, fixtureField, effectField);
	return { root, timeInput: tc.input, fixtureDropdown, effectDropdown };
}

export function buildMiddle(initialDuration: number): MiddleRefs {
	const root = document.createElement("div");
	root.className = "effect-picker-middle";
	const stack = document.createElement("div");
	stack.className = "effect-picker-param-stack";
	const durationInput = Input({
		caption: "Duration",
		bindings: {
			type: "number",
			value: String(initialDuration),
			min: 0,
			max: 20,
			step: 0.1,
			inputMode: "decimal",
			className: "effect-picker-duration-input",
			attributes: { "aria-label": "Effect duration in seconds" },
		},
	});
	const durationRow = document.createElement("div");
	durationRow.className = "effect-picker-duration";
	const durationLabel = document.createElement("span");
	durationLabel.className = "effect-picker-param-name";
	durationLabel.textContent = "duration";
	durationRow.append(durationInput.root, durationLabel);
	stack.appendChild(durationRow);
	const paramFormContainer = document.createElement("div");
	paramFormContainer.className = "effect-picker-params";
	stack.appendChild(paramFormContainer);
	root.appendChild(stack);
	return { root, durationInput, paramFormContainer };
}

export function buildActions(): ActionRefs {
	const root = document.createElement("div");
	root.className = "effect-picker-actions";
	const addGroup = document.createElement("div");
	addGroup.className = "effect-picker-action-group";
	const commitBtn = Button({ caption: "Add", icon: "playerPrev", state: "default", "icon-position": "start", bindings: { title: "Add cue at the current playback time" } });
	const cancelBtn = Button({ caption: "Cancel", icon: "delete", state: "default", "icon-position": "start", bindings: { title: "Cancel cue editing", disabled: true } });
	addGroup.append(commitBtn, cancelBtn);
	const previewGroup = document.createElement("div");
	previewGroup.className = "effect-picker-action-group effect-picker-action-group-preview";
	const previewBtn = Button({ caption: "Preview", icon: "playerPlay", state: "default", "icon-position": "end", bindings: { title: "Preview the selected effect" } });
	previewGroup.appendChild(previewBtn);
	root.append(addGroup, previewGroup);
	return { root, commitBtn, cancelBtn, previewBtn };
}
