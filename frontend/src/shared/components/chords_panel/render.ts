import type { ChordSectionGroup } from "./types.ts";

export function appendChordSection(sectionsRoot: HTMLElement, group: ChordSectionGroup): void {
	const block = document.createElement("section");
	block.className = "chords-panel-section";

	const label = document.createElement("p");
	label.className = "chords-panel-section-title";
	label.textContent = `${group.label} (${group.start_s.toFixed(2)}-${group.end_s.toFixed(2)})`;
	block.appendChild(label);

	const rowEl = document.createElement("div");
	rowEl.className = "chords-panel-row";

	for (const chord of group.chords) {
		const cell = document.createElement("span");
		cell.className = "chords-panel-cell";
		cell.textContent = chord.label;
		rowEl.appendChild(cell);
	}

	block.appendChild(rowEl);
	sectionsRoot.appendChild(block);
}