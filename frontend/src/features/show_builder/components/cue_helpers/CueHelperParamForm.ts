import { Dropdown } from "../../../../shared/components/controls/Dropdown.ts";
import { ColorPicker } from "../../../../shared/components/controls/ColorPicker.ts";
import { Input } from "../../../../shared/components/controls/Input.ts";
import { Slider } from "../../../../shared/components/controls/Slider.ts";
import type { CueHelperDefinition, CueHelperParameterDefinition } from "../../../../shared/transport/protocol.ts";
import { time_position } from "../time_position.ts";
import { formatTime } from "../effect_picker/selectors.ts";

type CueHelperParamFormProps = {
	helper: CueHelperDefinition;
	values: Record<string, unknown>;
	currentCursorMs: number;
	onChange: (name: string, value: unknown) => void;
};

function createNumberField(param: CueHelperParameterDefinition, value: unknown, onChange: (value: number) => void): HTMLElement {
	return Input({
		caption: param.label,
		bindings: {
			type: "number",
			value: String(value ?? param.default ?? 0),
			min: param.min,
			max: param.max,
			step: param.step,
			inputMode: "decimal",
			onChange: (_event, input) => onChange(Number(input.value)),
		},
	}).root;
}

function createRangeField(param: CueHelperParameterDefinition, value: unknown, onChange: (value: number) => void): HTMLElement {
	return Slider({
		label: param.label,
		min: Number(param.min ?? 0),
		max: Number(param.max ?? 1),
		step: Number(param.step ?? 0.1),
		value: Number(value ?? param.default ?? 0),
		onInput: onChange,
	}).root;
}

function createSelectField(param: CueHelperParameterDefinition, value: unknown, onChange: (value: string) => void): HTMLElement {
	return Dropdown({
		label: param.label,
		value: String(value ?? param.default ?? param.options?.[0]?.value ?? ""),
		options: param.options ?? [],
		onChange,
	}).root;
}

function createTimeField(label: string, valueMs: number): HTMLElement {
	const field = document.createElement("div");
	field.className = "cue-helper-field";

	const caption = document.createElement("span");
	caption.className = "input-control-label";
	caption.textContent = label;

	const control = time_position(formatTime(valueMs), `${label} at current song position`);
	field.append(caption, control.root);
	return field;
}

export function CueHelperParamForm(props: CueHelperParamFormProps): HTMLElement {
	const container = document.createElement("div");
	container.className = "cue-helper-form";

	if ((props.helper.parameters ?? []).length === 0) {
		const empty = document.createElement("p");
		empty.className = "cue-helper-empty";
		empty.textContent = "This helper has no parameters.";
		container.appendChild(empty);
		return container;
	}

	for (const param of props.helper.parameters ?? []) {
		const field = document.createElement("div");
		field.className = "cue-helper-field";
		const currentValue = param.name === "start_time_ms"
			? props.currentCursorMs
			: props.values[param.name];

		if (param.name === "start_time_ms") {
			container.appendChild(createTimeField(param.label, props.currentCursorMs));
			continue;
		}

		switch (param.type) {
			case "color":
				field.appendChild(ColorPicker({
					label: param.label,
					value: String(currentValue ?? param.default ?? "#FFFFFF"),
					onChange: (value) => props.onChange(param.name, value),
				}).root);
				break;
			case "range":
				field.appendChild(createRangeField(param, currentValue, (value) => props.onChange(param.name, value)));
				break;
			case "select":
				field.appendChild(createSelectField(param, currentValue, (value) => props.onChange(param.name, value)));
				break;
			case "number":
				field.appendChild(createNumberField(param, currentValue, (value) => props.onChange(param.name, value)));
				break;
			default:
				field.appendChild(Input({
					caption: param.label,
					bindings: {
						value: String(currentValue ?? param.default ?? ""),
						onChange: (_event, input) => props.onChange(param.name, input.value),
					},
				}).root);
		}
		container.appendChild(field);
	}

	return container;
}