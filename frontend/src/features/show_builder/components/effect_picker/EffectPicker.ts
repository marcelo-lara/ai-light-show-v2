import { Card } from "../../../../shared/components/layout/Card.ts";
import { subscribeBackendStore } from "../../../../shared/state/backend_state.ts";
import { previewEffect } from "../../../dmx_control/fixture_intents.ts";
import { addCue } from "../../cue_intents.ts";
import { getDefaultParams } from "../effect_params/params_schema.ts";
import { formatTime, getFixtures, getPlaybackTimeMs } from "./selectors.ts";
import { buildActions, buildMiddle, buildTopRow, createDivider } from "./layout.ts";
import { applyEffectOptions, applyFixtureOptions, renderParamForm } from "./updates.ts";
import type { PickerState } from "./types.ts";

export function EffectPicker(): HTMLElement {
	const content = document.createElement("div");
	content.className = "effect-picker-body";

	const state: PickerState = { fixtureId: "", effect: "", duration: 1, params: {} };

	const { root: topRoot, timeInput, fixtureSelect, effectSelect } = buildTopRow(formatTime(getPlaybackTimeMs()));
	const { root: middleRoot, durationInput, paramFormContainer } = buildMiddle(state.duration);
	const { root: actionsRoot, addBtn, previewBtn } = buildActions();

	const updateEffects = () => applyEffectOptions(state, effectSelect, paramFormContainer);
	const populate = () => applyFixtureOptions(fixtureSelect, state, updateEffects);

	fixtureSelect.addEventListener("change", () => {
		state.fixtureId = fixtureSelect.value;
		updateEffects();
	});
	effectSelect.addEventListener("change", () => {
		state.effect = effectSelect.value;
		state.params = getDefaultParams(state.effect);
		renderParamForm(state, paramFormContainer);
	});
	durationInput.addEventListener("input", () => {
		state.duration = Math.max(0, Number(durationInput.value));
	});
	addBtn.addEventListener("click", () => {
		if (!state.fixtureId || !state.effect) return;
		addCue(getPlaybackTimeMs() / 1000, state.fixtureId, state.effect, state.duration, state.params);
	});
	previewBtn.addEventListener("click", () => {
		if (!state.fixtureId || !state.effect) return;
		previewEffect(state.fixtureId, state.effect, state.duration * 1000, state.params);
	});

	const unsubscribe = subscribeBackendStore(() => {
		timeInput.value = formatTime(getPlaybackTimeMs());
		if (fixtureSelect.childElementCount !== getFixtures().length) populate();
	});

	populate();
	(content as unknown as { _cleanup: () => void })._cleanup = unsubscribe;
	content.append(topRoot, createDivider(), middleRoot, createDivider(), actionsRoot);
	return Card(content, { variant: "outlined", className: "show-builder-panel" });
}
