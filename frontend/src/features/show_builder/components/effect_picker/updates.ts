import { getDefaultParams } from "../effect_params/params_schema.ts";
import { ParamForm } from "../effect_params/ParamForm.ts";
import { getFixtures, getPois, getSupportedEffects } from "./selectors.ts";
import type { PickerState } from "./types.ts";
import type { DropdownControl } from "../../../../shared/components/controls/Dropdown.ts";

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
	effectDropdown: DropdownControl,
	paramContainer: HTMLElement,
): void {
	const effects = getSupportedEffects(state.fixtureId);
	effectDropdown.setOptions(effects.map((e) => ({ value: e, label: e })), state.effect);
	if (!effects.includes(state.effect)) {
		state.effect = effects.includes("flash") ? "flash" : (effects[0] ?? "");
		effectDropdown.setValue(state.effect);
		state.params = getDefaultParams(state.effect);
	}
	renderParamForm(state, paramContainer);
}

export function applyFixtureOptions(
	fixtureDropdown: DropdownControl,
	state: PickerState,
	onUpdated: () => void,
): void {
	const fixtures = getFixtures();
	const currentVal = fixtureDropdown.select.value;
	fixtureDropdown.setOptions(fixtures.map((f) => ({ value: f.id, label: f.name ?? f.id })), currentVal);
	if (fixtures.some((f) => f.id === currentVal)) {
		fixtureDropdown.setValue(currentVal);
		state.fixtureId = currentVal;
	} else if (fixtures.length > 0) {
		state.fixtureId = fixtures[0].id;
		fixtureDropdown.setValue(state.fixtureId);
	}
	onUpdated();
}
