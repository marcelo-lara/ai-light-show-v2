import { Button } from "../../../../shared/components/controls/Button.ts";
import { Dropdown, type DropdownOption } from "../../../../shared/components/controls/Dropdown.ts";
import { Card } from "../../../../shared/components/layout/Card.ts";
import { getBackendStore, subscribeBackendStore } from "../../../../shared/state/backend_state.ts";
import { previewEffect } from "../../../dmx_control/fixture_intents.ts";
import { applyChaser, previewChaser } from "../../cue_intents.ts";
import { getChasers } from "../effect_picker/selectors.ts";

export function ChaserPicker(): HTMLElement {
	const body = document.createElement("div");
	body.className = "chaser-picker-body";

	let selected = "";
	let repetitions = "1";
	let startTimeSeconds = 0;

	const head = document.createElement("div");
	head.className = "chaser-picker-head";

	const headControls = document.createElement("div");
	headControls.className = "chaser-picker-head-controls";

	const startTimeField = document.createElement("label");
	startTimeField.className = "chaser-picker-head-field";
	const startTimeInput = document.createElement("input");
	startTimeInput.type = "number";
	startTimeInput.min = "0";
	startTimeInput.step = "0.001";
	startTimeInput.className = "chaser-picker-start-input";
	startTimeInput.setAttribute("aria-label", "Start time");
	startTimeInput.addEventListener("input", () => {
		const value = Number(startTimeInput.value);
		startTimeSeconds = Number.isFinite(value) ? Math.max(0, value) : 0;
	});
	startTimeField.append(startTimeInput);

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
	chaserField.className = "chaser-picker-head-field chaser-picker-head-field--grow";
	chaserDropdown.root.classList.add("chaser-picker-field", "chaser-picker-field--compact");
	chaserDropdown.select.setAttribute("aria-label", "Chaser name");
	chaserField.append(chaserDropdown.root);

	const modeActions = document.createElement("div");
	modeActions.className = "chaser-picker-mode-actions";
	const newBtn = Button({
		caption: "New",
		icon: "addFile",
		bindings: {
			disabled: true,
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

	headControls.append(startTimeField, chaserField, modeActions);
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
	repsDropdown.root.classList.add("chaser-picker-field", "chaser-picker-field--small");

	const listHeader = document.createElement("div");
	listHeader.className = "chaser-picker-list-header muted";
	for (const titleText of ["", "", "", "", "", ""]) {
		const label = document.createElement("span");
		label.textContent = titleText;
		label.className = "chaser-picker-header-cell";
		listHeader.append(label);
	}

	const list = document.createElement("div");
	list.className = "chaser-picker-list";

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

	const actionRight = document.createElement("div");
	actionRight.className = "chaser-picker-action-group chaser-picker-action-group--right";
	actionRight.append(previewBtn);

	actions.append(actionLeft, actionRight);

	const empty = document.createElement("p");
	empty.className = "chaser-picker-empty";
	empty.textContent = "";

	function getStartTimeForBeat(beat: number, bpm: number): number {
		if (!Number.isFinite(bpm) || bpm <= 0) return 0;
		return (beat * 60) / bpm;
	}

	function renderEffects() {
		list.innerHTML = "";
		const chaser = getChasers().find((item) => item.name === selected);
		const bpm = Number(getBackendStore().state.playback?.bpm ?? getBackendStore().state.song?.bpm ?? 0);
		if (!chaser || chaser.effects.length === 0) {
			const emptyState = document.createElement("p");
			emptyState.className = "chaser-picker-empty";
			emptyState.textContent = "";
			list.append(emptyState);
			return;
		}

		for (const effect of [...chaser.effects].sort((a, b) => a.beat - b.beat)) {
			const row = document.createElement("div");
			row.className = "chaser-picker-row";

			const start = document.createElement("span");
			start.className = "chaser-picker-row__start";
			start.textContent = getStartTimeForBeat(effect.beat, bpm).toFixed(3);

			const beat = document.createElement("span");
			beat.className = "chaser-picker-row__beat";
			beat.textContent = String(effect.beat);

			const fixture = document.createElement("span");
			fixture.className = "chaser-picker-row__fixture";
			fixture.textContent = effect.fixture_id;

			const cueEffect = document.createElement("span");
			cueEffect.className = "chaser-picker-row__effect";
			cueEffect.textContent = effect.effect;

			const duration = document.createElement("span");
			duration.className = "chaser-picker-row__duration";
			duration.textContent = String(effect.duration);

			const preview = Button({
				icon: "preview",
				bindings: {
					onClick: () => {
						previewEffect(effect.fixture_id, effect.effect, effect.duration * 1000, effect.data);
					},
				},
			});
			preview.classList.add("chaser-picker-row__preview");

			row.append(start, beat, fixture, cueEffect, duration, preview);
			list.append(row);
		}
	}

	function refresh() {
		const playbackMs = Number(getBackendStore().state.playback?.time_ms ?? 0);
		startTimeSeconds = Math.max(0, playbackMs / 1000);
		startTimeInput.value = startTimeSeconds.toFixed(3);

		const chasers = getChasers();
		const options: DropdownOption[] = chasers.map((chaser) => ({
			value: chaser.name,
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
		renderEffects();
	}

	refresh();
	const unsubscribe = subscribeBackendStore(refresh);
	(body as unknown as { _cleanup: () => void })._cleanup = () => unsubscribe();

	body.append(head, repsDropdown.root, listHeader, list, divider, actions, empty);
	return Card(body, {
		title: "",
		variant: "outlined",
		className: "show-builder-panel show-builder-flow-card",
	});
}
