import { Card } from "../../../shared/components/layout/Card.ts";

type PlaylistRow = {
	time: string;
	fixture: string;
	effect: string;
	duration: string;
	params: string;
};

const PLAYLIST: PlaylistRow[] = [
	{ time: "0.0", fixture: "parcan_l", effect: "flash", duration: "1.0", params: "blue" },
	{ time: "12.0", fixture: "beam_1", effect: "strobe", duration: "2.0", params: "fast" },
	{ time: "24.2", fixture: "wash_center", effect: "pulse", duration: "4.0", params: "warm" },
];

export function EffectPlaylist(): HTMLElement {
	const content = document.createElement("div");
	content.className = "effect-playlist-body";

	const labels = document.createElement("p");
	labels.className = "effect-playlist-labels mono muted";
	labels.textContent = "time fixture effect duration parameters delete";
	content.appendChild(labels);

	for (const [index, row] of PLAYLIST.entries()) {
		const line = document.createElement("div");
		line.className = `effect-playlist-row mono${index === 0 ? " is-current" : ""}`;

		const left = document.createElement("span");
		left.textContent = `${row.time} ${row.fixture} ${row.effect} ${row.duration} ${row.params}`;

		const del = document.createElement("button");
		del.type = "button";
		del.className = "btn effect-playlist-delete";
		del.textContent = "x";

		line.append(left, del);
		content.appendChild(line);
	}

	return Card(content, { variant: "outlined", className: "show-builder-panel" });
}
