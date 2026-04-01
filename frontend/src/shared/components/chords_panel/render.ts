import type { BeatSectionGroup } from "./types.ts";
import { isDownbeat } from "../song_player/logic/song_logic.ts";

type AppendChordSectionOptions = {
	activeBeatIndex: number;
	beatOffset: number;
	onBeatSelect: (timeS: number) => void;
	onCellRender: (cell: HTMLElement, absoluteIndex: number) => void;
};

function displayLabel(chord?: string): string {
	if (!chord) return "";
	return chord.toUpperCase() === "N" ? "" : chord;
}

export function appendChordSection(
	sectionsRoot: HTMLElement,
	group: BeatSectionGroup,
	options: AppendChordSectionOptions,
): void {
	const block = document.createElement("section");
	block.className = "chords-panel-section";

	const label = document.createElement("p");
	label.className = "chords-panel-section-title";
	label.textContent = `${group.label} (${group.start_s.toFixed(3)}-${group.end_s.toFixed(3)})`;
	block.appendChild(label);

	const rowEl = document.createElement("div");
	rowEl.className = "chords-panel-row";

	for (const [index, beat] of group.beats.entries()) {
		const cell = document.createElement("span");
		const labelText = displayLabel(beat.chord);
		const absoluteIndex = options.beatOffset + index;
		const isActive = absoluteIndex === options.activeBeatIndex;
		const downbeatClass = isDownbeat(beat) ? " downbeat" : "";
		cell.className = `chords-panel-cell${labelText ? "" : " is-empty"}${isActive ? " is-active" : ""}${downbeatClass}`;
		cell.textContent = labelText;
		cell.tabIndex = 0;
		cell.setAttribute("role", "button");
		cell.setAttribute("aria-label", `Jump to beat ${beat.bar}.${beat.beat} at ${beat.time.toFixed(3)} seconds`);
		cell.onclick = () => options.onBeatSelect(beat.time);
		cell.onkeydown = (event) => {
			if (event.key !== "Enter" && event.key !== " ") return;
			event.preventDefault();
			options.onBeatSelect(beat.time);
		};
		options.onCellRender(cell, absoluteIndex);
		rowEl.appendChild(cell);
	}

	block.appendChild(rowEl);
	sectionsRoot.appendChild(block);
}