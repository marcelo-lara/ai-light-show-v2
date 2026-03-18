import { Card } from "../layout/Card.ts";
import { getSongPlayerTimeMs } from "../../state/song_player_time.ts";
import { selectPlayback } from "../../state/selectors.ts";
import { transportJumpToTime } from "../../transport/transport_intents.ts";
import { groupBeatsBySections } from "./grouping.ts";
import { appendChordSection } from "./render.ts";
import type { ChordsPanelProps } from "./types.ts";

const CHORD_SECTION_PAGE_SIZE = 3;
const ACTIVE_BEAT_SCROLL_PADDING_PX = 12;

function activeBeatIndex(beats: ChordsPanelProps["beats"], timeMs: number): number {
	if (!beats.length || !Number.isFinite(timeMs)) return -1;
	const timeS = Math.max(0, timeMs / 1000);
	for (let index = 0; index < beats.length; index++) {
		const start = Number(beats[index]?.time ?? 0) - 0.01;
		const next = beats[index + 1];
		const end = Number(next?.time ?? Number.POSITIVE_INFINITY);
		if (timeS > start && timeS < end) return index;
	}
	return -1;
}

export function ChordsPanel(props: ChordsPanelProps): HTMLElement {
	const content = document.createElement("div");
	content.className = "chords-panel";
	const playback = selectPlayback();
	const initialTimeMs = Math.max(playback.time_ms, getSongPlayerTimeMs());
	let currentBeatIndex = activeBeatIndex(props.beats, initialTimeMs);
	const cells: HTMLElement[] = [];
	console.debug("[CHORD_DEBUG] ChordsPanel props", {
		beats: props.beats.slice(0, 8),
		sections: props.sections.slice(0, 6),
		cardClassName: props.cardClassName,
		playbackTimeMs: initialTimeMs,
		currentBeatIndex,
	});

	if (!props.beats.length) {
		const empty = document.createElement("p");
		empty.className = "muted";
		empty.textContent = "No beat data for current song.";
		content.appendChild(empty);
		return Card(content, {
			ariaLabel: "Song Structure panel",
			variant: "outlined",
			className: props.cardClassName,
		});
	}

	const sectionsRoot = document.createElement("div");
	sectionsRoot.className = "chords-panel-sections";
	content.appendChild(sectionsRoot);

	const status = document.createElement("p");
	status.className = "muted";
	content.appendChild(status);

	const groups = groupBeatsBySections(props.beats, props.sections);
	console.debug("[CHORD_DEBUG] ChordsPanel groups", groups.slice(0, 6));
	let rendered = 0;
	let rafId = 0;

	const ensureBeatRendered = (beatIndex: number) => {
		while (beatIndex >= 0 && !cells[beatIndex] && rendered < groups.length) {
			renderNextPage();
		}
	};

	const scrollBeatIntoView = (beatIndex: number) => {
		if (beatIndex < 0) return;
		ensureBeatRendered(beatIndex);
		const cell = cells[beatIndex];
		if (!cell) return;

		const containerRect = content.getBoundingClientRect();
		const cellRect = cell.getBoundingClientRect();
		const topEdge = containerRect.top + ACTIVE_BEAT_SCROLL_PADDING_PX;
		const bottomEdge = containerRect.bottom - ACTIVE_BEAT_SCROLL_PADDING_PX;
		const isAbove = cellRect.top < topEdge;
		const isBelow = cellRect.bottom > bottomEdge;

		if (isAbove || isBelow) {
			cell.scrollIntoView({ block: "nearest", inline: "nearest" });
		}
	};

	const syncActiveBeat = () => {
		const nextBeatIndex = activeBeatIndex(props.beats, getSongPlayerTimeMs());
		if (nextBeatIndex !== currentBeatIndex) {
			if (currentBeatIndex >= 0) cells[currentBeatIndex]?.classList.remove("is-active");
			ensureBeatRendered(nextBeatIndex);
			if (nextBeatIndex >= 0) cells[nextBeatIndex]?.classList.add("is-active");
			scrollBeatIntoView(nextBeatIndex);
			currentBeatIndex = nextBeatIndex;
		}
		if (content.isConnected) {
			rafId = requestAnimationFrame(syncActiveBeat);
		}
	};

	const renderNextPage = () => {
		const next = groups.slice(rendered, rendered + CHORD_SECTION_PAGE_SIZE);
		let beatOffset = groups.slice(0, rendered).reduce((sum, group) => sum + group.beats.length, 0);
		for (const group of next) {
			appendChordSection(sectionsRoot, group, {
				activeBeatIndex: currentBeatIndex,
				beatOffset,
				onBeatSelect: (timeS) => transportJumpToTime(timeS * 1000),
				onCellRender: (cell, absoluteIndex) => {
					cells[absoluteIndex] = cell;
				},
			});
			beatOffset += group.beats.length;
		}
		rendered += next.length;
		const beatCount = next.reduce((sum, group) => sum + group.beats.length, 0);
		const shown = sectionsRoot.querySelectorAll(".chords-panel-cell").length;
		const total = props.beats.length;
		status.textContent = rendered < groups.length
			? `Showing ${shown} of ${total} beats.`
			: `Showing all ${total} beats.`;
		if (!beatCount && rendered < groups.length) renderNextPage();
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
	queueMicrotask(() => {
		if (!content.isConnected) return;
		scrollBeatIntoView(currentBeatIndex);
		rafId = requestAnimationFrame(syncActiveBeat);
	});
	content.addEventListener("DOMNodeRemovedFromDocument", () => {
		if (rafId) cancelAnimationFrame(rafId);
	}, { once: true });

	return Card(content, {
		ariaLabel: "Song Structure panel",
		variant: "outlined",
		className: props.cardClassName,
	});
}
