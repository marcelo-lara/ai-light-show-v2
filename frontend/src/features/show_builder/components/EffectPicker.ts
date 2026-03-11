import { Card } from "../../../shared/components/layout/Card.ts";

function selectControl(options: string[]): HTMLSelectElement {
	const select = document.createElement("select");
	for (const value of options) {
		const option = document.createElement("option");
		option.value = value;
		option.textContent = value;
		select.appendChild(option);
	}
	return select;
}

export function EffectPicker(): HTMLElement {
	const content = document.createElement("div");
	content.className = "effect-picker-body";

	const top = document.createElement("div");
	top.className = "effect-picker-top";

	const timeInput = document.createElement("input");
	timeInput.type = "text";
	timeInput.value = "12.542";

	const fixtureSelect = selectControl(["Parcan Left", "Parcan Right", "Beam 1", "Beam 2"]);
	top.append(timeInput, fixtureSelect);

	const middle = document.createElement("div");
	middle.className = "effect-picker-middle";
	const effectSelect = selectControl(["Flash", "Pulse", "Fade", "Strobe"]);

	const duration = document.createElement("input");
	duration.type = "number";
	duration.value = "1";

	const from = document.createElement("input");
	from.type = "number";
	from.value = "1";

	const to = document.createElement("input");
	to.type = "number";
	to.value = "0";

	middle.append(effectSelect, duration, from, to);

	const actions = document.createElement("div");
	actions.className = "effect-picker-actions";

	const add = document.createElement("button");
	add.type = "button";
	add.className = "btn";
	add.textContent = "< Add";

	const preview = document.createElement("button");
	preview.type = "button";
	preview.className = "btn";
	preview.textContent = "preview";

	actions.append(add, preview);
	content.append(top, middle, actions);

	return Card(content, { variant: "outlined", className: "show-builder-panel" });
}
