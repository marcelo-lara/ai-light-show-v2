import type { Poi } from "../../../../shared/transport/protocol.ts";
import type { ParamDef } from "./params_schema.ts";
import { getEffectSchema } from "./params_schema.ts";

export type ParamFormProps = {
	effectName: string;
	values: Record<string, unknown>;
	pois: Poi[];
	onChange: (name: string, value: unknown) => void;
};

function createNumberInput(param: ParamDef, value: unknown, onChange: (v: number) => void): HTMLElement {
	const wrap = document.createElement("label");
	wrap.className = "param-field";

	const label = document.createElement("span");
	label.className = "param-label";
	label.textContent = param.label;

	const input = document.createElement("input");
	input.type = "number";
	input.className = "param-input";
	input.value = String(value ?? param.default ?? 0);
	if (param.min !== undefined) input.min = String(param.min);
	if (param.max !== undefined) input.max = String(param.max);
	if (param.step !== undefined) input.step = String(param.step);

	input.addEventListener("input", () => {
		onChange(Number(input.value));
	});

	wrap.append(label, input);
	return wrap;
}

function createRangeInput(param: ParamDef, value: unknown, onChange: (v: number) => void): HTMLElement {
	const wrap = document.createElement("label");
	wrap.className = "param-field param-field--range";

	const label = document.createElement("span");
	label.className = "param-label";
	label.textContent = param.label;

	const rangeWrap = document.createElement("div");
	rangeWrap.className = "param-range-wrap";

	const input = document.createElement("input");
	input.type = "range";
	input.className = "param-range";
	input.value = String(value ?? param.default ?? 0);
	if (param.min !== undefined) input.min = String(param.min);
	if (param.max !== undefined) input.max = String(param.max);
	if (param.step !== undefined) input.step = String(param.step);

	const display = document.createElement("span");
	display.className = "param-value mono";
	display.textContent = input.value;

	input.addEventListener("input", () => {
		display.textContent = input.value;
		onChange(Number(input.value));
	});

	rangeWrap.append(input, display);
	wrap.append(label, rangeWrap);
	return wrap;
}

function createPoiSelect(param: ParamDef, value: unknown, pois: Poi[], onChange: (v: string) => void): HTMLElement {
	const wrap = document.createElement("label");
	wrap.className = "param-field";

	const label = document.createElement("span");
	label.className = "param-label";
	label.textContent = param.label;

	const select = document.createElement("select");
	select.className = "param-select";

	// Empty option for optional POIs
	const emptyOpt = document.createElement("option");
	emptyOpt.value = "";
	emptyOpt.textContent = "— Select POI —";
	select.appendChild(emptyOpt);

	for (const poi of pois) {
		const opt = document.createElement("option");
		opt.value = poi.name;
		opt.textContent = poi.name;
		if (poi.name === value) opt.selected = true;
		select.appendChild(opt);
	}

	select.addEventListener("change", () => {
		onChange(select.value);
	});

	wrap.append(label, select);
	return wrap;
}

function createSelectInput(param: ParamDef, value: unknown, onChange: (v: string) => void): HTMLElement {
	const wrap = document.createElement("label");
	wrap.className = "param-field";

	const label = document.createElement("span");
	label.className = "param-label";
	label.textContent = param.label;

	const select = document.createElement("select");
	select.className = "param-select";

	for (const option of param.options || []) {
		const opt = document.createElement("option");
		opt.value = option;
		opt.textContent = option;
		if (option === value) opt.selected = true;
		select.appendChild(opt);
	}

	select.addEventListener("change", () => {
		onChange(select.value);
	});

	wrap.append(label, select);
	return wrap;
}

export function ParamForm(props: ParamFormProps): HTMLElement {
	const { effectName, values, pois, onChange } = props;
	const container = document.createElement("div");
	container.className = "param-form";

	const schema = getEffectSchema(effectName);
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
