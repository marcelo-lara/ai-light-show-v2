import { Card } from "../../../shared/components/layout/Card.ts";
import { List } from "../../../shared/components/layout/List.ts";
import { Button } from "../../../shared/components/controls/Button.ts";
import { Input } from "../../../shared/components/controls/Input.ts";
import { ConfirmCancelPrompt } from "../../../shared/components/feedback/ConfirmCancelPrompt.ts";
import { getBackendStore, subscribeBackendStore } from "../../../shared/state/backend_state.ts";
import { getSongPlayerTimeMs } from "../../../shared/state/song_player_time.ts";
import { selectEditLock } from "../../../shared/state/selectors.ts";
import { transportJumpToTime } from "../../../shared/transport/transport_intents.ts";
import { createHumanHint, deleteHumanHint, updateHumanHint } from "../song_analysis_intents.ts";
import { readHumanHints, type HumanHint } from "./HumanHints.ts";

type Draft = { mode: "create" | "edit"; id?: string; startTime: string; endTime: string; title: string; summary: string; lightingHint: string };

const formatTime = (value: number) => (Number.isFinite(value) ? value.toFixed(3) : "0.000");
const text = (className: string, value: string) => Object.assign(document.createElement("p"), { className, textContent: value });

function createEditor(draft: Draft, onSave: () => void, onCancel: () => void): HTMLElement {
	const editor = document.createElement("div");
	editor.className = "human-hints-editor";
	const top = document.createElement("div");
	top.className = "human-hints-editor-top";
	top.append(text("human-hints-editor-time", draft.mode === "create" ? "Create human hint" : "Edit human hint"));
	const startTime = Input({ caption: "Start", bindings: { type: "number", step: "0.001", value: draft.startTime, onInput: (_event, input) => draft.startTime = input.value } });
	const startTimeRow = document.createElement("div");
	startTimeRow.className = "human-hints-editor-time-row";
	const setStartTimeToCursor = Button({
		caption: "Cursor",
		bindings: {
			title: "Set start time to current cursor position",
			onClick: () => {
				draft.startTime = formatTime(Math.max(0, getSongPlayerTimeMs() / 1000));
				startTime.setValue(draft.startTime);
			},
		},
	});
	startTimeRow.append(startTime.root, setStartTimeToCursor);
	const endTime = Input({ caption: "End", bindings: { type: "number", step: "0.001", value: draft.endTime, onInput: (_event, input) => draft.endTime = input.value } });
	const endTimeRow = document.createElement("div");
	endTimeRow.className = "human-hints-editor-time-row";
	const setEndTimeToCursor = Button({
		caption: "Cursor",
		bindings: {
			title: "Set end time to current cursor position",
			onClick: () => {
				draft.endTime = formatTime(Math.max(0, getSongPlayerTimeMs() / 1000));
				endTime.setValue(draft.endTime);
			},
		},
	});
	endTimeRow.append(endTime.root, setEndTimeToCursor);
	const title = Input({ caption: "Title", bindings: { value: draft.title, onInput: (_event, input) => draft.title = input.value } });
	const summary = document.createElement("textarea");
	summary.className = "human-hints-textarea";
	summary.rows = 2;
	summary.value = draft.summary;
	summary.placeholder = "Summary";
	summary.addEventListener("input", () => draft.summary = summary.value);
	const lightingHint = document.createElement("textarea");
	lightingHint.className = "human-hints-textarea";
	lightingHint.rows = 3;
	lightingHint.value = draft.lightingHint;
	lightingHint.placeholder = "Lighting hint";
	lightingHint.addEventListener("input", () => draft.lightingHint = lightingHint.value);
	const actions = document.createElement("div");
	actions.className = "human-hints-editor-actions";
	actions.append(
		Button({ caption: "Cancel", bindings: { onClick: () => onCancel() } }),
		Button({ caption: draft.mode === "create" ? "Add" : "Save", state: "primary", bindings: { onClick: () => onSave() } }),
	);
	editor.append(top, startTimeRow, endTimeRow, title.root, summary, lightingHint, actions);
	return editor;
}

function buildRow(hint: HumanHint, isActive: boolean, disabled: boolean, onEdit: () => void, onDelete: () => void): HTMLElement {
	const main = document.createElement("div");
	main.className = "human-hints-row-main";
	main.append(
		text("human-hints-row-title", hint.title || "Untitled hint"),
		text("human-hints-row-time muted", `${formatTime(hint.startTime)} - ${formatTime(hint.endTime)}`),
	);
	if (hint.summary) main.append(text("human-hints-row-copy", hint.summary));
	if (hint.lightingHint) main.append(text("human-hints-row-copy muted", hint.lightingHint));
	return List({
		className: "human-hints-row",
		content: main,
		actions: [
			Button({ caption: "Edit", bindings: { disabled, onClick: () => onEdit() } }),
			Button({ caption: "Delete", bindings: { disabled, onClick: () => onDelete() } }),
		],
		isActive,
		onSelect: () => transportJumpToTime(hint.startTime * 1000),
		title: hint.id,
		dataset: { hintId: hint.id },
	});
}

export function HumanHintsPanel(): HTMLElement {
	const content = document.createElement("div");
	content.className = "human-hints-panel";
	const header = document.createElement("div");
	header.className = "human-hints-header";
	const title = text("human-hints-title", "Human Hints");
	const meta = text("human-hints-meta muted", "");
	const addButton = Button({ caption: "Add", state: "primary" });
	header.append(title, meta, addButton);
	const body = document.createElement("div");
	body.className = "human-hints-body o-list";
	content.append(header, body);
	let draft: Draft | null = null;

	const render = () => {
		const song = getBackendStore().state.song;
		const analysis = readHumanHints(song?.analysis?.human_hints ?? [], song?.analysis?.human_hints_status);
		const disabled = selectEditLock() === true || !song?.filename;
		const cursorS = Math.max(0, getSongPlayerTimeMs() / 1000);
		meta.textContent = `${analysis.items.length} hints · ${analysis.status.fileExists ? (analysis.status.saved ? "saved" : "dirty") : "not created"}`;
		addButton.disabled = disabled || draft !== null;
		addButton.onclick = () => {
			if (disabled || draft) return;
			draft = { mode: "create", startTime: formatTime(cursorS), endTime: formatTime(cursorS + 1), title: "", summary: "", lightingHint: "" };
			render();
		};
		body.replaceChildren();
		if (draft) {
			body.append(createEditor(draft, () => {
				const startTime = Number(draft?.startTime ?? 0);
				const endTime = Number(draft?.endTime ?? draft?.startTime ?? 0);
				if (!draft || !Number.isFinite(startTime) || !Number.isFinite(endTime)) return;
				const normalizedStartTime = Math.max(0, startTime);
				const normalizedEndTime = Math.max(normalizedStartTime, endTime);
				if (draft.mode === "create") {
					createHumanHint({ start_time: normalizedStartTime, end_time: normalizedEndTime, title: draft.title.trim(), summary: draft.summary.trim(), lighting_hint: draft.lightingHint.trim() });
				} else if (draft.id) {
					updateHumanHint(draft.id, { start_time: normalizedStartTime, end_time: normalizedEndTime, title: draft.title.trim(), summary: draft.summary.trim(), lighting_hint: draft.lightingHint.trim() });
				}
				draft = null;
				render();
			}, () => {
				draft = null;
				render();
			}));
		}
		if (!analysis.items.length) {
			body.append(text("human-hints-empty muted", "No human hints for current song."));
			return;
		}
		for (const hint of analysis.items) {
			body.append(buildRow(hint, cursorS >= hint.startTime && cursorS < hint.endTime, disabled, () => {
				draft = { mode: "edit", id: hint.id, startTime: formatTime(hint.startTime), endTime: formatTime(hint.endTime), title: hint.title, summary: hint.summary, lightingHint: hint.lightingHint };
				render();
			}, async () => {
				const confirmed = await ConfirmCancelPrompt({ title: "Delete human hint", message: `Delete ${hint.title || hint.id}?`, confirmLabel: "Delete", cancelLabel: "Cancel" });
				if (confirmed) deleteHumanHint(hint.id);
			}));
		}
	};

	render();
	const unsubscribe = subscribeBackendStore(render);
	const card = Card(content, { variant: "outlined", className: "human-hints-card" });
	(card as unknown as { _cleanup?: () => void })._cleanup = () => unsubscribe();
	return card;
}