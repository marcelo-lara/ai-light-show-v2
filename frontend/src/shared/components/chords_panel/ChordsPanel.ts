import { Card } from "../layout/Card.ts";
import { groupChordsBySections } from "./grouping.ts";
import { appendChordSection } from "./render.ts";
import type { ChordsPanelProps } from "./types.ts";

const CHORD_SECTION_PAGE_SIZE = 3;

export function ChordsPanel(props: ChordsPanelProps): HTMLElement {
	const content = document.createElement("div");
	content.className = "chords-panel";

	if (!props.chords.length) {
		const empty = document.createElement("p");
		empty.className = "muted";
		empty.textContent = "No chord data for current song.";
		content.appendChild(empty);
		return Card(content, { variant: "outlined", className: props.cardClassName });
	}

	const sectionsRoot = document.createElement("div");
	sectionsRoot.className = "chords-panel-sections";
	content.appendChild(sectionsRoot);

	const status = document.createElement("p");
	status.className = "muted";
	content.appendChild(status);

	const groups = groupChordsBySections(props.chords, props.sections);
	let rendered = 0;

	const renderNextPage = () => {
		const next = groups.slice(rendered, rendered + CHORD_SECTION_PAGE_SIZE);
		for (const group of next) appendChordSection(sectionsRoot, group);
		rendered += next.length;
		const chordCount = next.reduce((sum, group) => sum + group.chords.length, 0);
		const shown = sectionsRoot.querySelectorAll(".chords-panel-cell").length;
		const total = props.chords.length;
		status.textContent = rendered < groups.length
			? `Showing ${shown} of ${total} chord changes.`
			: `Showing all ${total} chord changes.`;
		if (!chordCount && rendered < groups.length) renderNextPage();
	};

	const fillUntilScrollable = () => {
		while (rendered < groups.length && content.scrollHeight <= content.clientHeight) {
			renderNextPage();
		}
	};

	content.addEventListener("scroll", () => {
		if (rendered >= groups.length) return;
		const threshold = content.scrollHeight - content.clientHeight - 24;
		if (content.scrollTop >= threshold) {
			renderNextPage();
			fillUntilScrollable();
		}
	});

	renderNextPage();
	queueMicrotask(fillUntilScrollable);

	return Card(content, { variant: "outlined", className: props.cardClassName });
}