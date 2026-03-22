import type { Poi } from "../../../../shared/transport/protocol.ts";
import { Dropdown } from "../../../../shared/components/controls/Dropdown.ts";
import { Slider } from "../../../../shared/components/controls/Slider.ts";
import type { ParamDef } from "./params_schema.ts";
import { getEffectSchema } from "./params_schema.ts";

export type ParamFormProps = {
	effectName: string;
	fixtureType?: string;
	values: Record<string, unknown>;
	pois: Poi[];
	onChange: (name: string, value: unknown) => void;
};

function createNumberInput(param: ParamDef, value: unknown, onChange: (v: number) => void): HTMLElement {
	const wrap = document.createElement("div");
	wrap.className = "param-field";

	const slider = Slider({
		label: param.label,
		min: param.min ?? 0,
		max: param.max ?? 255,
		step: param.step ?? 1,
		value: Number(value ?? param.default ?? 0),
		className: "param-input",
		onInput: onChange,
	});

	wrap.appendChild(slider.root);
	return wrap;
}

function createRangeInput(param: ParamDef, value: unknown, onChange: (v: number) => void): HTMLElement {
	const wrap = document.createElement("div");
	wrap.className = "param-field param-field-range";

	const slider = Slider({
		label: param.label,
		min: param.min ?? 0,
		max: param.max ?? 255,
		step: param.step ?? 1,
		value: Number(value ?? param.default ?? 0),
		className: "param-range",
		onInput: onChange,
	});

	wrap.appendChild(slider.root);
	return wrap;
}

function createPoiSelect(param: ParamDef, value: unknown, pois: Poi[], onChange: (v: string) => void): HTMLElement {
	const wrap = document.createElement("div");
	wrap.className = "param-field";

	const dropdown = Dropdown({
		label: param.label,
		value: String(value ?? ""),
		options: [
			{ value: "", label: "- Select POI -" },
			...pois.map((poi) => ({ value: poi.name, label: poi.name })),
		],
		onChange,
	});

	wrap.appendChild(dropdown.root);
	return wrap;
}

function createSelectInput(param: ParamDef, value: unknown, onChange: (v: string) => void): HTMLElement {
	const wrap = document.createElement("div");
	wrap.className = "param-field";

	const dropdown = Dropdown({
		label: param.label,
		value: String(value ?? param.options?.[0] ?? ""),
		options: (param.options || []).map((option) => ({ value: option, label: option })),
		onChange,
	});

	wrap.appendChild(dropdown.root);
	return wrap;
}

export function ParamForm(props: ParamFormProps): HTMLElement {
	const { effectName, fixtureType, values, pois, onChange } = props;
	const container = document.createElement("div");
	container.className = "param-form";

	const schema = getEffectSchema(effectName, fixtureType);
	if (!schema || schema.params.length === 0) {
		const empty = document.createElement("p");
		empty.className = "muted";
		empty.textContent = "No parameters for this effect";
		container.appendChild(empty);
		return container;
	}

	for (const param of schema.params) {
		const currentValue = values[param.name];

		let field: HTMLElement;
		switch (param.type) {
			case "number":
				field = createNumberInput(param, currentValue, (v) => onChange(param.name, v));
				break;
			case "range":
				field = createRangeInput(param, currentValue, (v) => onChange(param.name, v));
				break;
			case "poi":
				field = createPoiSelect(param, currentValue, pois, (v) => onChange(param.name, v));
				break;
			case "select":
				field = createSelectInput(param, currentValue, (v) => onChange(param.name, v));
				break;
			default:
				field = createNumberInput(param, currentValue, (v) => onChange(param.name, v));
		}

		container.appendChild(field);
	}

	return container;
}
