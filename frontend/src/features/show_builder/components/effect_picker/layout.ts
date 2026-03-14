import { Input } from "../../../../shared/components/controls/Input.ts";
import { Button } from "../../../../shared/components/controls/Button.ts";
import { Dropdown, type DropdownControl } from "../../../../shared/components/controls/Dropdown.ts";
import { Slider, type SliderControl } from "../../../../shared/components/controls/Slider.ts";

export type TopRowRefs = {
	root: HTMLElement;
	timeInput: HTMLInputElement;
	fixtureDropdown: DropdownControl;
	effectDropdown: DropdownControl;
};

export type MiddleRefs = {
	root: HTMLElement;
	durationSlider: SliderControl;
	paramFormContainer: HTMLElement;
};

export type ActionRefs = {
	root: HTMLElement;
	modeLabel: HTMLSpanElement;
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
	const timeField = field("effect-picker-field--time");
	const tc = Input({ state: "default", "icon-position": "start", bindings: { value: timeValue, readOnly: true, className: "effect-picker-time", type: "text", attributes: { "aria-label": "Current playback time" } } });
	timeField.appendChild(tc.root);
	const fixtureField = field("effect-picker-field--fixture");
	const fixtureDropdown = Dropdown({
		value: "",
		options: [],
		selectClassName: "effect-picker-select",
		attributes: { "aria-label": "Fixture" },
	});
	fixtureField.appendChild(fixtureDropdown.root);
	const effectField = field("effect-picker-field--effect");
	const effectDropdown = Dropdown({
		value: "",
		options: [],
		selectClassName: "effect-picker-select",
		attributes: { "aria-label": "Effect" },
	});
	effectField.appendChild(effectDropdown.root);
	root.append(timeField, fixtureField, effectField);
	return { root, timeInput: tc.input, fixtureDropdown, effectDropdown };
}

export function buildMiddle(initialDuration: number): MiddleRefs {
	const root = document.createElement("div");
	root.className = "effect-picker-middle";
	const stack = document.createElement("div");
	stack.className = "effect-picker-param-stack";
	const durationSlider = Slider({
		label: "Duration",
		min: 0,
		max: 20,
		step: 0.1,
		value: initialDuration,
		className: "effect-picker-duration-input",
		onInput: () => {},
	});
	const durationRow = document.createElement("div");
	durationRow.className = "effect-picker-duration";
	const durationLabel = document.createElement("span");
	durationLabel.className = "effect-picker-param-name";
	durationLabel.textContent = "duration";
	durationRow.append(durationSlider.root, durationLabel);
	stack.appendChild(durationRow);
	const paramFormContainer = document.createElement("div");
	paramFormContainer.className = "effect-picker-params";
	stack.appendChild(paramFormContainer);
	root.appendChild(stack);
	return { root, durationSlider, paramFormContainer };
}

export function buildActions(): ActionRefs {
	const root = document.createElement("div");
	root.className = "effect-picker-actions";
	const modeLabel = document.createElement("span");
	modeLabel.className = "effect-picker-mode muted";
	modeLabel.textContent = "Add mode";
	const addGroup = document.createElement("div");
	addGroup.className = "effect-picker-action-group";
	const commitBtn = Button({ caption: "Add", icon: "playerPrev", state: "default", "icon-position": "start", bindings: { title: "Add cue at the current playback time" } });
	const cancelBtn = Button({ caption: "Cancel", icon: "delete", state: "default", "icon-position": "start", bindings: { title: "Cancel cue editing", className: "effect-picker-cancel", disabled: true } });
	addGroup.append(modeLabel, commitBtn, cancelBtn);
	const previewGroup = document.createElement("div");
	previewGroup.className = "effect-picker-action-group effect-picker-action-group--preview";
	const previewBtn = Button({ caption: "Preview", icon: "playerPlay", state: "default", "icon-position": "end", bindings: { title: "Preview the selected effect" } });
	previewGroup.appendChild(previewBtn);
	root.append(addGroup, previewGroup);
	return { root, modeLabel, commitBtn, cancelBtn, previewBtn };
}
