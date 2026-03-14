import { Card } from "../../../shared/components/layout/Card.ts";
import { getBackendStore, subscribeBackendStore } from "../../../shared/state/backend_state.ts";
import { previewEffect } from "../../dmx_control/fixture_intents.ts";
import { addCue } from "../cue_intents.ts";
import { ParamForm } from "./effect_params/ParamForm.ts";
import { getDefaultParams } from "./effect_params/params_schema.ts";

type PickerState = {
	fixtureId: string;
	effect: string;
	duration: number;
	params: Record<string, unknown>;
};

function formatTime(ms: number): string {
	const s = ms / 1000;
	return s.toFixed(3);
}

export function EffectPicker(): HTMLElement {
	const content = document.createElement("div");
	content.className = "effect-picker-body";

	// Local state
	const state: PickerState = {
		fixtureId: "",
		effect: "",
		duration: 1,
		params: {},
	};

	// DOM references for reactive updates
	let timeInput: HTMLInputElement;
	let fixtureSelect: HTMLSelectElement;
	let effectSelect: HTMLSelectElement;
	let durationInput: HTMLInputElement;
	let paramFormContainer: HTMLElement;

	function getStore() {
		return getBackendStore().state;
	}

	function getFixtures() {
		return Object.values(getStore().fixtures ?? {});
	}

	function getPois() {
		return getStore().pois ?? [];
	}

	function getPlaybackTimeMs() {
		return getStore().playback?.time_ms ?? 0;
	}

	function getSelectedFixture() {
		const fixtures = getStore().fixtures ?? {};
		return fixtures[state.fixtureId];
	}

	function getSupportedEffects(): string[] {
		const fixture = getSelectedFixture();
		return fixture?.supported_effects ?? [];
	}

	function updateEffectDropdown() {
		const effects = getSupportedEffects();
		effectSelect.innerHTML = "";

		for (const effect of effects) {
			const opt = document.createElement("option");
			opt.value = effect;
			opt.textContent = effect;
			if (effect === state.effect) opt.selected = true;
			effectSelect.appendChild(opt);
		}

		// If current effect is not in the list, switch to flash or first available
		if (!effects.includes(state.effect)) {
			if (effects.includes("flash")) {
				state.effect = "flash";
			} else {
				state.effect = effects[0] ?? "";
			}
			effectSelect.value = state.effect;
			state.params = getDefaultParams(state.effect);
		}

		updateParamForm();
	}

	function updateParamForm() {
		paramFormContainer.innerHTML = "";
		const form = ParamForm({
			effectName: state.effect,
			values: state.params,
			pois: getPois(),
			onChange: (name, value) => {
				state.params[name] = value;
			},
		});
		paramFormContainer.appendChild(form);
	}

	function updateTimeDisplay() {
		timeInput.value = formatTime(getPlaybackTimeMs());
	}

	// Build layout
	const top = document.createElement("div");
	top.className = "effect-picker-top";

	timeInput = document.createElement("input");
	timeInput.type = "text";
	timeInput.readOnly = true;
	timeInput.className = "mono";
	timeInput.value = formatTime(getPlaybackTimeMs());

	fixtureSelect = document.createElement("select");
	fixtureSelect.addEventListener("change", () => {
		state.fixtureId = fixtureSelect.value;
		updateEffectDropdown();
	});

	top.append(timeInput, fixtureSelect);

	const middle = document.createElement("div");
	middle.className = "effect-picker-middle";

	effectSelect = document.createElement("select");
	effectSelect.addEventListener("change", () => {
		state.effect = effectSelect.value;
		state.params = getDefaultParams(state.effect);
		updateParamForm();
	});

	durationInput = document.createElement("input");
	durationInput.type = "number";
	durationInput.value = String(state.duration);
	durationInput.min = "0";
	durationInput.step = "0.1";
	durationInput.addEventListener("input", () => {
		state.duration = Math.max(0, Number(durationInput.value));
	});

	const durationLabel = document.createElement("label");
	durationLabel.className = "effect-picker-duration";
	const durationSpan = document.createElement("span");
	durationSpan.textContent = "Duration";
	durationLabel.append(durationSpan, durationInput);

	middle.append(effectSelect, durationLabel);

	// Param form container
	paramFormContainer = document.createElement("div");
	paramFormContainer.className = "effect-picker-params";

	const actions = document.createElement("div");
	actions.className = "effect-picker-actions";

	const addBtn = document.createElement("button");
	addBtn.type = "button";
	addBtn.className = "btn";
	addBtn.textContent = "< Add";
	addBtn.addEventListener("click", () => {
		if (!state.fixtureId || !state.effect) return;
		const time = getPlaybackTimeMs() / 1000;
		addCue(time, state.fixtureId, state.effect, state.duration, state.params);
	});

	const previewBtn = document.createElement("button");
	previewBtn.type = "button";
	previewBtn.className = "btn";
	previewBtn.textContent = "preview";
	previewBtn.addEventListener("click", () => {
		if (!state.fixtureId || !state.effect) return;
		const durationMs = state.duration * 1000;
		previewEffect(state.fixtureId, state.effect, durationMs, state.params);
	});

	actions.append(addBtn, previewBtn);
	content.append(top, middle, paramFormContainer, actions);

	// Initialize fixture dropdown from state
	function populateFixtures() {
		const fixtures = getFixtures();
		const currentVal = fixtureSelect.value;
		fixtureSelect.innerHTML = "";

		for (const fixture of fixtures) {
			const opt = document.createElement("option");
			opt.value = fixture.id;
			opt.textContent = fixture.name ?? fixture.id;
			fixtureSelect.appendChild(opt);
		}

		// Restore selection or select first
		if (fixtures.some((f) => f.id === currentVal)) {
			fixtureSelect.value = currentVal;
			state.fixtureId = currentVal;
		} else if (fixtures.length > 0) {
			state.fixtureId = fixtures[0].id;
			fixtureSelect.value = state.fixtureId;
		}

		updateEffectDropdown();
	}

	// Subscribe to state changes
	const unsubscribe = subscribeBackendStore(() => {
		updateTimeDisplay();
		// Re-populate fixtures if they changed
		const fixtures = getFixtures();
		if (fixtureSelect.childElementCount !== fixtures.length) {
			populateFixtures();
		}
	});

	// Initial population
	populateFixtures();

	// Cleanup on removal (for future use with proper component lifecycle)
	(content as unknown as { _cleanup: () => void })._cleanup = unsubscribe;

	return Card(content, { variant: "outlined", className: "show-builder-panel" });
}
