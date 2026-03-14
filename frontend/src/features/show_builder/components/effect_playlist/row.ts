import { Button } from "../../../../shared/components/controls/Button.ts";
import type { CueEntry } from "../../../../shared/transport/protocol.ts";
import { formatCueLabel, formatCueParams, formatCueTime } from "./format.ts";

function createText(tagName: keyof HTMLElementTagNameMap, className: string, text: string): HTMLElement {
	const node = document.createElement(tagName);
	node.className = className;
	node.textContent = text;
	return node;
}

function createAction(icon: "delete" | "edit", title: string, className = ""): HTMLButtonElement {
	return Button({
		icon,
		bindings: { className: `effect-playlist-action ${className}`.trim(), title },
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

export function createCueRow(cue: CueEntry): HTMLElement {
	const row = document.createElement("article");
	row.className = "effect-playlist-row";
	row.dataset.time = String(cue.time);

	const meta = document.createElement("div");
	meta.className = "effect-playlist-row__meta";
	meta.append(
		createText("span", "effect-playlist-row__time", formatCueTime(cue.time)),
		createText("span", "effect-playlist-row__duration", `${cue.duration.toFixed(1)}s`),
	);

	const copy = document.createElement("div");
	copy.className = "effect-playlist-row__copy";
	copy.append(
		createText("p", "effect-playlist-row__fixture muted", formatCueLabel(cue.fixture_id)),
		createText("h3", "effect-playlist-row__effect", formatCueLabel(cue.effect)),
	);

	const params = document.createElement("div");
	params.className = "effect-playlist-row__params";
	for (const param of formatCueParams(cue.data)) {
		params.appendChild(createText("span", "effect-playlist-row__param", param));
	}

	const main = document.createElement("div");
	main.className = "effect-playlist-row__main";
	main.append(meta, copy, params);

	const actions = document.createElement("div");
	actions.className = "effect-playlist-row__actions";
	actions.append(
		createAction("edit", "Edit cue"),
		createAction("delete", "Delete cue"),
	);

	row.append(main, actions);
	return row;
}