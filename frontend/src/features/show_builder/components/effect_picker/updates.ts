import { getDefaultParams } from "../effect_params/params_schema.ts";
import { ParamForm } from "../effect_params/ParamForm.ts";
import { getFixtures, getPois, getSupportedEffects } from "./selectors.ts";
import type { PickerState } from "./types.ts";

export function renderParamForm(state: PickerState, container: HTMLElement): void {
	container.innerHTML = "";
	container.appendChild(ParamForm({
		effectName: state.effect,
		values: state.params,
		pois: getPois(),
		onChange: (name, value) => { state.params[name] = value; },
	}));
}

export function applyEffectOptions(
	state: PickerState,
	effectSelect: HTMLSelectElement,
	paramContainer: HTMLElement,
): void {
	const effects = getSupportedEffects(state.fixtureId);
	effectSelect.innerHTML = "";
	for (const e of effects) {
		const opt = document.createElement("option");
		opt.value = e;
		opt.textContent = e;
		if (e === state.effect) opt.selected = true;
		effectSelect.appendChild(opt);
	}
	if (!effects.includes(state.effect)) {
		state.effect = effects.includes("flash") ? "flash" : (effects[0] ?? "");
		effectSelect.value = state.effect;
		state.params = getDefaultParams(state.effect);
	}
	renderParamForm(state, paramContainer);
}

export function applyFixtureOptions(
	fixtureSelect: HTMLSelectElement,
	state: PickerState,
	onUpdated: () => void,
): void {
	const fixtures = getFixtures();
	const currentVal = fixtureSelect.value;
	fixtureSelect.innerHTML = "";
	for (const f of fixtures) {
		const opt = document.createElement("option");
		opt.value = f.id;
		opt.textContent = f.name ?? f.id;
		fixtureSelect.appendChild(opt);
	}
	if (fixtures.some((f) => f.id === currentVal)) {
		fixtureSelect.value = currentVal;
		state.fixtureId = currentVal;
	} else if (fixtures.length > 0) {
		state.fixtureId = fixtures[0].id;
		fixtureSelect.value = state.fixtureId;
	}
	onUpdated();
}
