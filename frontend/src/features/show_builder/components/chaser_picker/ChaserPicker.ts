import { Button } from "../../../../shared/components/controls/Button.ts";
import { Dropdown, type DropdownOption } from "../../../../shared/components/controls/Dropdown.ts";
import { Card } from "../../../../shared/components/layout/Card.ts";
import { List } from "../../../../shared/components/layout/List.ts";
import { getBackendStore, subscribeBackendStore } from "../../../../shared/state/backend_state.ts";
import type { CueEntry } from "../../../../shared/transport/protocol.ts";
import { previewEffect } from "../../../dmx_control/fixture_intents.ts";
import { applyChaser, previewChaser, updateCue } from "../../cue_intents.ts";
import { getChaserById, getCueRepetitions, isChaserCue } from "../../cue_utils.ts";
import { formatTime, getChasers } from "../effect_picker/selectors.ts";
import { time_position } from "../time_position.ts";

type CueEditEvent = CustomEvent<{ index: number; cue: CueEntry }>;

export function ChaserPicker(): HTMLElement {
	const body = document.createElement("div");
	body.className = "chaser-picker-body";

	let selected = "";
	let repetitions = "1";
	let startTimeSeconds = 0;
	let editingIndex: number | null = null;
	let editingTimeSeconds: number | null = null;

	const head = document.createElement("div");
	head.className = "chaser-picker-head";

	const headControls = document.createElement("div");
	headControls.className = "chaser-picker-head-controls";

	const startTime = time_position(formatTime(0), "Current playback time");
	startTime.root.classList.add("chaser-picker-head-field", "time_position-field");
	const startTimeInput = startTime.input;

	const chaserDropdown = Dropdown({
		label: "",
		value: "",
		options: [],
		onChange: (value) => {
			selected = value;
			renderEffects();
		},
	});
	const chaserField = document.createElement("div");
	chaserField.className = "chaser-picker-head-field chaser-picker-head-field-grow";
	chaserDropdown.root.classList.add("chaser-picker-field", "chaser-picker-field-compact");
	chaserDropdown.select.setAttribute("aria-label", "Chaser name");
	chaserField.append(chaserDropdown.root);

	const modeActions = document.createElement("div");
	modeActions.className = "chaser-picker-mode-actions";
	const newBtn = Button({
		caption: "New",
		icon: "addFile",
		bindings: {
			disabled: true,
			onClick: () => {
				editingIndex = null;
				editingTimeSeconds = null;
				refreshActionMode();
				refresh();
			},
		},
	});
	const editBtn = Button({
		caption: "Edit",
		icon: "edit",
		bindings: {
			disabled: true,
		},
	});
	modeActions.append(newBtn, editBtn);

	headControls.append(startTime.root, chaserField, modeActions);
	head.append(headControls);

	const repsDropdown = Dropdown({
		label: "",
		value: repetitions,
		options: Array.from({ length: 8 }, (_, i) => {
			const n = String(i + 1);
			return { value: n, label: n };
		}),
		onChange: (value) => {
			repetitions = value;
		},
	});
	repsDropdown.root.classList.add("chaser-picker-field", "chaser-picker-field-small");

	const list = document.createElement("div");
	list.className = "chaser-picker-list o-list";

	const divider = document.createElement("div");
	divider.className = "chaser-picker-divider";

	const actions = document.createElement("div");
	actions.className = "chaser-picker-actions";

	const addBtn = Button({
		caption: "Add",
		icon: "addFile",
		state: "primary",
		bindings: {
			onClick: () => {
				if (!selected) return;
				if (editingIndex !== null) {
					updateCue(editingIndex, {
						time: editingTimeSeconds ?? startTimeSeconds,
						chaser_id: selected,
						data: { repetitions: Number(repetitions) },
					});
					editingIndex = null;
					editingTimeSeconds = null;
					refreshActionMode();
					return;
				}
				applyChaser(selected, startTimeSeconds * 1000, Number(repetitions));
			},
		},
	});

	const previewBtn = Button({
		caption: "Preview",
		icon: "preview",
		bindings: {
			onClick: () => {
				if (!selected) return;
				previewChaser(selected, startTimeSeconds * 1000, Number(repetitions));
			},
		},
	});

	const actionLeft = document.createElement("div");
	actionLeft.className = "chaser-picker-action-group";
	actionLeft.append(addBtn);

	actionLeft.append(repsDropdown.root);

	const actionRight = document.createElement("div");
	actionRight.className = "chaser-picker-action-group chaser-picker-action-group-right";
	actionRight.append(previewBtn);

	actions.append(actionLeft, actionRight);

	const empty = document.createElement("p");
	empty.className = "chaser-picker-empty";
	empty.textContent = "";

	function refreshActionMode() {
		const isEditing = editingIndex !== null;
		addBtn.querySelector(".btn-caption")!.textContent = isEditing ? "Update" : "Add";
		newBtn.disabled = !isEditing;
		editBtn.disabled = true;
	}

	function getStartTimeForBeat(beat: number, bpm: number): number {
		if (!Number.isFinite(bpm) || bpm <= 0) return 0;
		return (beat * 60) / bpm;
	}

	function renderEffects() {
		list.innerHTML = "";
		const chaser = getChaserById(getChasers(), selected);
		const bpm = Number(getBackendStore().state.playback?.bpm ?? getBackendStore().state.song?.bpm ?? 0);
		if (!chaser || chaser.effects.length === 0) {
			const emptyState = document.createElement("p");
			emptyState.className = "chaser-picker-empty";
			emptyState.textContent = "";
			list.append(emptyState);
			return;
		}

		for (const effect of [...chaser.effects].sort((a, b) => a.beat - b.beat)) {
			const start = document.createElement("span");
			start.className = "u-cell u-cell-time";
			start.textContent = getStartTimeForBeat(effect.beat, bpm).toFixed(3);

			const beat = document.createElement("span");
			beat.className = "u-cell u-cell-beat";
			beat.textContent = String(effect.beat);

			const fixture = document.createElement("span");
			fixture.className = "u-cell u-cell-fixture";
			fixture.textContent = effect.fixture_id;

			const cueEffect = document.createElement("span");
			cueEffect.className = "u-cell u-cell-effect";
			cueEffect.textContent = effect.effect;

			const duration = document.createElement("span");
			duration.className = "u-cell u-cell-duration";
			duration.textContent = `${getStartTimeForBeat(effect.duration, bpm).toFixed(3)}s`;

			const preview = Button({
				icon: "preview",
				bindings: {
					onClick: () => {
						previewEffect(
							effect.fixture_id,
							effect.effect,
							getStartTimeForBeat(effect.duration, bpm) * 1000,
							effect.data,
						);
					},
				},
			});
			preview.classList.add("chaser-picker-row-preview");

			const content = document.createElement("div");
			content.append(start, beat, fixture, cueEffect, duration);

			const actions = document.createElement("div");
			actions.append(preview);

			const row = List({
				tagName: "div",
				className: "chaser-picker-row",
				content,
				actions,
			});
			list.append(row);
		}
	}

	function applyCueToPicker(index: number, cue: CueEntry) {
		if (!isChaserCue(cue)) return;
		selected = cue.chaser_id;
		repetitions = String(getCueRepetitions(cue));
		editingIndex = index;
		editingTimeSeconds = cue.time;
		startTimeSeconds = cue.time;
		startTimeInput.value = formatTime(cue.time * 1000);
		repsDropdown.setValue(repetitions);
		refreshActionMode();
		renderEffects();
	}

	function refresh() {
		const playbackMs = Number(getBackendStore().state.playback?.time_ms ?? 0);
		if (editingTimeSeconds === null) {
			startTimeSeconds = Math.max(0, playbackMs / 1000);
			startTimeInput.value = formatTime(playbackMs);
		}

		const chasers = getChasers();
		const options: DropdownOption[] = chasers.map((chaser) => ({
			value: chaser.id,
			label: chaser.name,
		}));
		const nextValue = options.some((option) => option.value === selected) ? selected : (options[0]?.value ?? "");
		selected = nextValue;
		chaserDropdown.setOptions(options, nextValue);

		const disabled = options.length === 0;
		chaserDropdown.select.disabled = disabled;
		repsDropdown.select.disabled = disabled;
		startTimeInput.disabled = disabled;
		previewBtn.disabled = disabled;
		addBtn.disabled = disabled;
		empty.style.display = disabled ? "block" : "none";
		refreshActionMode();
		renderEffects();
	}

	const onCueEdit = (event: Event) => {
		const customEvent = event as CueEditEvent;
		if (!customEvent.detail) return;
		if (!isChaserCue(customEvent.detail.cue)) return;
		applyCueToPicker(customEvent.detail.index, customEvent.detail.cue);
	};
	window.addEventListener("show-builder:cue-edit", onCueEdit as EventListener);

	refresh();
	const unsubscribe = subscribeBackendStore(refresh);
	(body as unknown as { _cleanup: () => void })._cleanup = () => {
		unsubscribe();
		window.removeEventListener("show-builder:cue-edit", onCueEdit as EventListener);
	};

	body.append(head, list, divider, actions, empty);
	return Card(body, {
		title: "",
		variant: "outlined",
		className: "show-builder-panel show-builder-flow-card",
	});
}
