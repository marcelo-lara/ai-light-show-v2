import { Button } from "../../../../shared/components/controls/Button.ts";
import { List } from "../../../../shared/components/layout/List.ts";
import type { CueEntry } from "../../../../shared/transport/protocol.ts";
import { formatCueLabel, formatCueTime } from "./format.ts";

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
		createText("p", "cue-sheet-empty__eyebrow muted", "Cue Sheet"),
		createText("h3", "cue-sheet-empty__title", "No cues queued yet"),
		createText("p", "cue-sheet-empty__copy muted", "Add cues from the picker to build the show timeline."),
	);
	return empty;
}

export function createCueRow(cue: CueEntry, handlers: CueRowHandlers): HTMLElement {
	const main = document.createElement("div");
	main.append(
		createText("span", "u-cell u-cell-time", formatCueTime(cue.time)),
		createText("span", "u-cell u-cell-fixture", formatCueLabel(cue.fixture_id)),
		createText("span", "u-cell u-cell-effect", formatCueLabel(cue.effect)),
		createText("span", "u-cell u-cell-duration", `${cue.duration.toFixed(1)}s`),
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