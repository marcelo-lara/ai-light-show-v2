import { Card } from "../../../shared/components/layout/Card.ts";
import type { SongChord } from "../../../shared/transport/protocol.ts";

type ChordsPanelProps = {
  chords: SongChord[];
};

export function ChordsPanel(props: ChordsPanelProps): HTMLElement {
	const content = document.createElement("div");
	content.className = "analysis-card";

	const title = document.createElement("h3");
	title.textContent = "Chords";
	content.appendChild(title);

	if (!props.chords.length) {
		const empty = document.createElement("p");
		empty.textContent = "No chord data for current song.";
		content.appendChild(empty);
		return Card(content, { variant: "outlined" });
	}

	const list = document.createElement("ol");
	list.className = "analysis-list mono";
	const preview = props.chords.slice(0, 24);
	for (const chord of preview) {
		const item = document.createElement("li");
		const beatRef = chord.bar !== undefined && chord.beat !== undefined
			? ` | ${chord.bar}.${chord.beat}`
			: "";
		item.textContent = `${chord.time_s.toFixed(3)}s | ${chord.label}${beatRef}`;
		list.appendChild(item);
	}
	content.appendChild(list);

	if (props.chords.length > preview.length) {
		const more = document.createElement("p");
		more.className = "muted";
		more.textContent = `Showing first ${preview.length} chord changes.`;
		content.appendChild(more);
	}

	return Card(content, { variant: "outlined" });
}
