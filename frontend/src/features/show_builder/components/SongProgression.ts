import { Card } from "../../../shared/components/layout/Card.ts";

type ProgressBlock = {
	label: string;
	rows: string[][];
};

const BLOCKS: ProgressBlock[] = [
	{ label: "Intro", rows: [["", "", "", ""], ["Cm", "", "", ""], ["F", "", "", ""]] },
	{ label: "Verse", rows: [["", "", "", ""], ["", "", "", ""]] },
];

export function SongProgression(): HTMLElement {
	const content = document.createElement("div");
	content.className = "song-progression-body";

	for (const [index, block] of BLOCKS.entries()) {
		const item = document.createElement("section");
		item.className = `song-progression-item${index === 0 ? " is-current" : ""}`;

		const blockEl = document.createElement("article");
		blockEl.className = "song-progression-block";

		const title = document.createElement("p");
		title.className = "song-progression-title";
		title.textContent = block.label;

		for (const [rowIndex, row] of block.rows.entries()) {
			const rowEl = document.createElement("div");
			rowEl.className = "song-progression-row";

			for (const [chordIndex, chord] of row.entries()) {
				const cell = document.createElement("span");
				const isCurrentCell = index === 0 && rowIndex === 0 && chordIndex === 0;
				cell.className = `song-progression-cell mono${isCurrentCell ? " is-current" : ""}`;
				cell.textContent = chord;
				rowEl.appendChild(cell);
			}

			blockEl.appendChild(rowEl);
		}

		item.append(title, blockEl);
		content.appendChild(item);
	}

	return Card(content, { variant: "outlined", className: "show-builder-panel" });
}
