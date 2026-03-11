import { Card } from "../../../shared/components/layout/Card.ts";
import type { SongChord } from "../../../shared/transport/protocol.ts";

type ChordsPanelProps = {
  chords: SongChord[];
};

const CHORD_SECTION_SIZE = 8;
const SECTION_NAMES = ["Intro", "Verse", "Pre-Chorus", "Chorus", "Bridge", "Outro"];

type ChordSection = {
	name: string;
	rows: string[][];
};

function buildSectionRows(chords: SongChord[], offset: number): string[][] {
	const labels = chords.slice(offset, offset + 8).map((chord) => chord.label);
	const padded = [...labels];
	while (padded.length < 8) padded.push("");
	return [padded.slice(0, 4), padded.slice(4, 8)];
}

export function ChordsPanel(props: ChordsPanelProps): HTMLElement {
	const content = document.createElement("div");
	content.className = "analysis-card analysis-chords";

	const title = document.createElement("h3");
	title.textContent = "Chords";
	content.appendChild(title);

	if (!props.chords.length) {
		const empty = document.createElement("p");
		empty.className = "muted";
		empty.textContent = "No chord data for current song.";
		content.appendChild(empty);
		return Card(content, { variant: "outlined" });
	}

	const sectionsRoot = document.createElement("div");
	sectionsRoot.className = "chords-sections";
	content.appendChild(sectionsRoot);

	const status = document.createElement("p");
	status.className = "muted";
	content.appendChild(status);

	let rendered = 0;

	const appendSection = (section: ChordSection) => {
		const block = document.createElement("section");
		block.className = "chords-section";

		const label = document.createElement("p");
		label.className = "chords-section-title";
		label.textContent = section.name;
		block.appendChild(label);

		for (const row of section.rows) {
			const rowEl = document.createElement("div");
			rowEl.className = "chords-row";

			for (const chord of row) {
				const cell = document.createElement("span");
				cell.className = "chords-cell";
				cell.textContent = chord;
				rowEl.appendChild(cell);
			}

			block.appendChild(rowEl);
		}

		sectionsRoot.appendChild(block);
	};

	const renderNextSection = () => {
		if (rendered >= props.chords.length) return;
		const sectionIndex = Math.floor(rendered / CHORD_SECTION_SIZE);
		appendSection({
			name: SECTION_NAMES[sectionIndex] ?? `Section ${sectionIndex + 1}`,
			rows: buildSectionRows(props.chords, rendered),
		});
		rendered += Math.min(CHORD_SECTION_SIZE, props.chords.length - rendered);
		status.textContent = rendered < props.chords.length
			? `Showing ${rendered} of ${props.chords.length} chord changes.`
			: `Showing all ${props.chords.length} chord changes.`;
	};

	const fillUntilScrollable = () => {
		while (rendered < props.chords.length && content.scrollHeight <= content.clientHeight) {
			renderNextSection();
		}
	};

	content.addEventListener("scroll", () => {
		if (rendered >= props.chords.length) return;
		const threshold = content.scrollHeight - content.clientHeight - 24;
		if (content.scrollTop >= threshold) {
			renderNextSection();
			fillUntilScrollable();
		}
	});

	renderNextSection();
	queueMicrotask(fillUntilScrollable);

	return Card(content, { variant: "outlined" });
}
