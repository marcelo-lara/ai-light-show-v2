import { Button } from "../../../../shared/components/controls/Button.ts";
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
	className = "",
): HTMLButtonElement {
	return Button({
		icon,
		bindings: { className: `effect-playlist-action ${className}`.trim(), title, onClick },
	});
}

export function createEmptyPlaylistState(): HTMLElement {
	const empty = document.createElement("section");
	empty.className = "effect-playlist-empty";
	empty.append(
		createText("p", "effect-playlist-empty__eyebrow muted", "Playlist"),
		createText("h3", "effect-playlist-empty__title", "No effects queued yet"),
		createText("p", "effect-playlist-empty__copy muted", "Add effects from the picker to build the show timeline."),
	);
	return empty;
}

export function createCueRow(cue: CueEntry, handlers: CueRowHandlers): HTMLElement {
	const row = document.createElement("article");
	row.className = "effect-playlist-row";
	row.dataset.time = String(cue.time);

	const main = document.createElement("div");
	main.className = "effect-playlist-row__main";
	main.addEventListener("click", handlers.onSelect);
	main.append(
		createText("span", "effect-playlist-row__time", formatCueTime(cue.time)),
		createText("span", "effect-playlist-row__fixture", formatCueLabel(cue.fixture_id)),
		createText("span", "effect-playlist-row__effect", formatCueLabel(cue.effect)),
		createText("span", "effect-playlist-row__duration", `${cue.duration.toFixed(1)}s`),
	);

	const actions = document.createElement("div");
	actions.className = "effect-playlist-row__actions";
	actions.append(
		createAction("delete", "Delete cue", handlers.onDelete, "effect-playlist-action--delete"),
		createAction("preview", "Preview cue", handlers.onPreview, "effect-playlist-action--preview"),
		createAction("edit", "Edit cue", handlers.onEdit, "effect-playlist-action--edit"),
	);

	row.append(main, actions);
	row.title = JSON.stringify(cue.data ?? {});
	return row;
}