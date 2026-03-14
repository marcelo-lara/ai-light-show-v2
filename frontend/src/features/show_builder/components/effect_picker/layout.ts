import { Input } from "../../../../shared/components/controls/Input.ts";
import { Button } from "../../../../shared/components/controls/Button.ts";

export type TopRowRefs = {
	root: HTMLElement;
	timeInput: HTMLInputElement;
	fixtureSelect: HTMLSelectElement;
	effectSelect: HTMLSelectElement;
};

export type MiddleRefs = {
	root: HTMLElement;
	durationInput: HTMLInputElement;
	paramFormContainer: HTMLElement;
};

export type ActionRefs = {
	root: HTMLElement;
	addBtn: HTMLButtonElement;
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
	const fixtureSelect = document.createElement("select");
	fixtureSelect.className = "effect-picker-select";
	fixtureSelect.setAttribute("aria-label", "Fixture");
	fixtureField.appendChild(fixtureSelect);
	const effectField = field("effect-picker-field--effect");
	const effectSelect = document.createElement("select");
	effectSelect.className = "effect-picker-select";
	effectSelect.setAttribute("aria-label", "Effect");
	effectField.appendChild(effectSelect);
	root.append(timeField, fixtureField, effectField);
	return { root, timeInput: tc.input, fixtureSelect, effectSelect };
}

export function buildMiddle(initialDuration: number): MiddleRefs {
	const root = document.createElement("div");
	root.className = "effect-picker-middle";
	const stack = document.createElement("div");
	stack.className = "effect-picker-param-stack";
	const dc = Input({ state: "default", "icon-position": "start", bindings: { type: "number", value: String(initialDuration), min: 0, step: 0.1, className: "effect-picker-duration-input", inputMode: "decimal" } });
	const durationRow = document.createElement("div");
	durationRow.className = "effect-picker-duration";
	const durationLabel = document.createElement("span");
	durationLabel.className = "effect-picker-param-name";
	durationLabel.textContent = "duration";
	durationRow.append(dc.root, durationLabel);
	stack.appendChild(durationRow);
	const paramFormContainer = document.createElement("div");
	paramFormContainer.className = "effect-picker-params";
	stack.appendChild(paramFormContainer);
	root.appendChild(stack);
	return { root, durationInput: dc.input, paramFormContainer };
}

export function buildActions(): ActionRefs {
	const root = document.createElement("div");
	root.className = "effect-picker-actions";
	const addGroup = document.createElement("div");
	addGroup.className = "effect-picker-action-group";
	const addBtn = Button({ caption: "Add", icon: "playerPrev", state: "default", "icon-position": "start", bindings: { title: "Add cue at the current playback time" } });
	addGroup.appendChild(addBtn);
	const previewGroup = document.createElement("div");
	previewGroup.className = "effect-picker-action-group effect-picker-action-group--preview";
	const previewBtn = Button({ caption: "Preview", icon: "playerPlay", state: "default", "icon-position": "end", bindings: { title: "Preview the selected effect" } });
	previewGroup.appendChild(previewBtn);
	root.append(addGroup, previewGroup);
	return { root, addBtn, previewBtn };
}
