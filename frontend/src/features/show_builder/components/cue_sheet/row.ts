import { Button } from "../../../../shared/components/controls/Button.ts";
import { getBackendStore } from "../../../../shared/state/backend_state.ts";
import { List } from "../../../../shared/components/layout/List.ts";
import type { CueEntry } from "../../../../shared/transport/protocol.ts";
import {
	formatCueLabel,
	getChaserById,
	getCueDurationSeconds,
	isChaserCue,
	isEffectCue,
} from "../../cue_utils.ts";
import { formatCueTime } from "./format.ts";

type CueRowHandlers = {
	onEdit: () => void;
	onPreview: () => void;
	onDelete: () => void;
	onSelect: () => void;
};

function createText(tagName: keyof HTMLElementTagNameMap, className: string, text: string): HTMLElement {
	const node = document.createElement(tagName);
	node.className = className;
	node.textContent = text;
	return node;
}

function createAction(
	icon: "delete" | "preview" | "edit",
	title: string,
	onClick: () => void,
): HTMLButtonElement {
	return Button({
		icon,
		bindings: { title, onClick },
	});
}

export function createEmptyCueSheetState(): HTMLElement {
	const empty = document.createElement("section");
	empty.className = "cue-sheet-empty";
	empty.append(
		createText("p", "cue-sheet-empty-eyebrow muted", "Cue Sheet"),
		createText("h3", "cue-sheet-empty-title", "No cues queued yet"),
		createText("p", "cue-sheet-empty-copy muted", "Add cues from the picker to build the show timeline."),
	);
	return empty;
}

export function createCueRow(cue: CueEntry, handlers: CueRowHandlers): HTMLElement {
	const main = document.createElement("div");
	const bpm = Number(getBackendStore().state.playback?.bpm ?? getBackendStore().state.song?.bpm ?? 0);
	const chasers = getBackendStore().state.chasers ?? [];
	main.append(createText("span", "u-cell u-cell-time", formatCueTime(cue.time)));
	if (isEffectCue(cue)) {
		main.append(
			createText("span", "u-cell u-cell-fixture", formatCueLabel(cue.fixture_id)),
			createText("span", "u-cell u-cell-effect", formatCueLabel(cue.effect)),
		);
	}
	if (isChaserCue(cue)) {
		const chaser = getChaserById(chasers, cue.chaser_id);
		main.append(createText("span", "u-cell u-cell-effect", chaser?.name ?? formatCueLabel(cue.chaser_id)));
	}
	main.append(
		createText("span", "u-cell u-cell-duration", `${getCueDurationSeconds(cue, chasers, bpm).toFixed(1)}s`),
	);

	const actions = document.createElement("div");
	actions.append(
		createAction("delete", "Delete cue", handlers.onDelete),
		createAction("preview", "Preview cue", handlers.onPreview),
		createAction("edit", "Edit cue", handlers.onEdit),
	);

	return List({
		className: "cue-sheet-row",
		content: main,
		actions,
		onSelect: handlers.onSelect,
		dataset: { time: String(cue.time) },
		title: JSON.stringify(cue.data ?? {}),
	});
}
