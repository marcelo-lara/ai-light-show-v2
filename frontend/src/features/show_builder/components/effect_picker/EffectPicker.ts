import { Card } from "../../../../shared/components/layout/Card.ts";
import type { CueEntry } from "../../../../shared/transport/protocol.ts";
import { subscribeBackendStore } from "../../../../shared/state/backend_state.ts";
import { previewEffect } from "../../../dmx_control/fixture_intents.ts";
import { addCue, updateCue } from "../../cue_intents.ts";
import { getDefaultParams } from "../effect_params/params_schema.ts";
import { formatTime, getFixtures, getPlaybackTimeMs } from "./selectors.ts";
import { buildActions, buildMiddle, buildTopRow, createDivider } from "./layout.ts";
import { applyEffectOptions, applyFixtureOptions, renderParamForm } from "./updates.ts";
import type { PickerState } from "./types.ts";

type CueEditEvent = CustomEvent<{ index: number; cue: CueEntry }>;

export function EffectPicker(): HTMLElement {
	const content = document.createElement("div");
	content.className = "effect-picker-body";

	const state: PickerState = {
		fixtureId: "",
		effect: "",
		duration: 1,
		params: {},
		editingIndex: null,
		editingTime: null,
	};

	const { root: topRoot, timeInput, fixtureDropdown, effectDropdown } = buildTopRow(formatTime(getPlaybackTimeMs()));
	const { root: middleRoot, durationSlider, paramFormContainer } = buildMiddle(state.duration);
	const { root: actionsRoot, commitBtn, cancelBtn, previewBtn } = buildActions();

	const refreshActionMode = () => {
		const isEditing = state.editingIndex !== null;
		commitBtn.querySelector(".btn-caption")!.textContent = isEditing ? "Update" : "Add";
		commitBtn.title = isEditing ? "Update selected cue" : "Add cue at the current playback time";
		cancelBtn.disabled = !isEditing;
	};

	const resetEditState = () => {
		state.editingIndex = null;
		state.editingTime = null;
		refreshActionMode();
	};

	const applyCueToPicker = (index: number, cue: CueEntry) => {
		state.editingIndex = index;
		state.editingTime = cue.time;
		state.fixtureId = cue.fixture_id;
		fixtureDropdown.setValue(cue.fixture_id);
		applyEffectOptions(state, effectDropdown, paramFormContainer);
		state.effect = cue.effect;
		effectDropdown.setValue(cue.effect);
		state.duration = Number(cue.duration) || 0;
		durationSlider.setValue(state.duration);
		state.params = { ...(cue.data ?? {}) };
		renderParamForm(state, paramFormContainer);
		refreshActionMode();
	};

	const updateEffects = () => applyEffectOptions(state, effectDropdown, paramFormContainer);
	const populate = () => applyFixtureOptions(fixtureDropdown, state, updateEffects);

	fixtureDropdown.select.addEventListener("change", () => {
		state.fixtureId = fixtureDropdown.select.value;
		updateEffects();
	});
	effectDropdown.select.addEventListener("change", () => {
		state.effect = effectDropdown.select.value;
		state.params = getDefaultParams(state.effect);
		renderParamForm(state, paramFormContainer);
	});
	durationSlider.input.addEventListener("input", () => {
		state.duration = Math.max(0, Number(durationSlider.input.value));
	});
	commitBtn.addEventListener("click", () => {
		if (!state.fixtureId || !state.effect) return;
		if (state.editingIndex !== null) {
			updateCue(state.editingIndex, {
				time: state.editingTime ?? getPlaybackTimeMs() / 1000,
				fixture_id: state.fixtureId,
				effect: state.effect,
				duration: state.duration,
				data: state.params,
			});
			resetEditState();
			return;
		}
		addCue(getPlaybackTimeMs() / 1000, state.fixtureId, state.effect, state.duration, state.params);
	});
	cancelBtn.addEventListener("click", () => {
		resetEditState();
	});
	previewBtn.addEventListener("click", () => {
		if (!state.fixtureId || !state.effect) return;
		previewEffect(state.fixtureId, state.effect, state.duration * 1000, state.params);
	});

	const onCueEdit = (event: Event) => {
		const customEvent = event as CueEditEvent;
		if (!customEvent.detail) return;
		applyCueToPicker(customEvent.detail.index, customEvent.detail.cue);
	};
	window.addEventListener("show-builder:cue-edit", onCueEdit as EventListener);

	const unsubscribe = subscribeBackendStore(() => {
		timeInput.value = formatTime(getPlaybackTimeMs());
		if (fixtureDropdown.select.childElementCount !== getFixtures().length) populate();
	});

	populate();
	refreshActionMode();
	(content as unknown as { _cleanup: () => void })._cleanup = () => {
		unsubscribe();
		window.removeEventListener("show-builder:cue-edit", onCueEdit as EventListener);
	};
	content.append(topRoot, createDivider(), middleRoot, createDivider(), actionsRoot);
	return Card(content, { variant: "outlined", className: "show-builder-panel" });
}
