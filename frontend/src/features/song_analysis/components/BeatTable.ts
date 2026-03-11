import { Card } from "../../../shared/components/layout/Card.ts";

type BeatTableProps = {
  beats: number[];
  downbeats: number[];
};

export function BeatTable(props: BeatTableProps): HTMLElement {
	const content = document.createElement("div");
	content.className = "analysis-card";

	const title = document.createElement("h3");
	title.textContent = "Beat Table";
	content.appendChild(title);

	if (!props.beats.length) {
		const empty = document.createElement("p");
		empty.textContent = "No beat data for current song.";
		content.appendChild(empty);
		return Card(content, { variant: "outlined" });
	}

	const stats = document.createElement("p");
	stats.className = "muted";
	stats.textContent = `Beats: ${props.beats.length} | Downbeats: ${props.downbeats.length}`;
	content.appendChild(stats);

	const list = document.createElement("ol");
	list.className = "analysis-list mono";
	const preview = props.beats.slice(0, 24);
	for (const beat of preview) {
		const item = document.createElement("li");
		item.textContent = `${beat.toFixed(3)}s${props.downbeats.includes(beat) ? "  (downbeat)" : ""}`;
		list.appendChild(item);
	}
	content.appendChild(list);

	if (props.beats.length > preview.length) {
		const more = document.createElement("p");
		more.className = "muted";
		more.textContent = `Showing first ${preview.length} rows.`;
		content.appendChild(more);
	}

	return Card(content, { variant: "outlined" });
}
