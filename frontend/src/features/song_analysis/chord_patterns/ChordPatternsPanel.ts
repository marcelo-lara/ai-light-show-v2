import { Card } from "../../../shared/components/layout/Card.ts";
import { Cards } from "../../../shared/components/layout/Cards.ts";
import { getSongPlayerTimeMs } from "../../../shared/state/song_player_time.ts";
import { selectPlayback } from "../../../shared/state/selectors.ts";
import { ChordPatterns } from "./ChordPatterns.ts";

function formatTime(value: number): string {
	return Number.isFinite(value) ? value.toFixed(3) : "0.000";
}

function text(className: string, value: string): HTMLParagraphElement {
	const node = document.createElement("p");
	node.className = className;
	node.textContent = value;
	return node;
}

function occurrenceLabel(startBar: number, endBar: number, startTime: number, endTime: number): string {
	return `${endBar - startBar}: ${formatTime(startTime)}-${formatTime(endTime)}`;
}

export function ChordPatternsPanel(patterns: ChordPatterns): HTMLElement {
	const activeSquares = new Map<string, HTMLElement>();
	const cards = patterns.items.map((pattern, patternIndex) => {
		const body = document.createElement("div");
		body.className = "chord-pattern-card-body";
		body.append(
			text("chord-pattern-card-title", `Pattern ${pattern.label}`),
			text("chord-pattern-card-meta muted", `${pattern.occurrenceCount} occurrences · ${pattern.barCount} bars`),
			text("chord-pattern-card-sequence", pattern.sequence),
		);

		const occurrences = document.createElement("div");
		occurrences.className = "chord-pattern-occurrences";
		pattern.occurrences.forEach((occurrence, occurrenceIndex) => {
			const square = document.createElement("div");
			square.className = "chord-pattern-occurrence";
			square.textContent = occurrenceLabel(occurrence.startBar, occurrence.endBar, occurrence.startTime, occurrence.endTime);
			square.title = occurrence.sequence || `${pattern.label} occurrence`;
			if (occurrence.mismatchCount > 0) square.dataset.mismatchCount = String(occurrence.mismatchCount);
			activeSquares.set(`${patternIndex}:${occurrenceIndex}`, square);
			occurrences.append(square);
		});

		body.append(occurrences);
		return Card(body, { variant: "outlined", className: "chord-pattern-card" });
	});

	const root = Cards(
		cards.length
			? cards
			: [Card(text("chord-patterns-empty muted", "No chord patterns available for current song."), { variant: "outlined", className: "chord-pattern-card" })],
		{ className: "chord-patterns-panel" },
	);

	if (!cards.length) return root;

	let currentKeys = patterns.activeOccurrenceKeys(Math.max(selectPlayback().time_ms, getSongPlayerTimeMs()));
		for (const [key, square] of activeSquares.entries()) square.classList.toggle("is-active", currentKeys.has(key));

	let rafId = 0;
	const syncActive = () => {
		const nextKeys = patterns.activeOccurrenceKeys(getSongPlayerTimeMs());
		if (nextKeys.size !== currentKeys.size || [...nextKeys].some((key) => !currentKeys.has(key))) {
			for (const [key, square] of activeSquares.entries()) square.classList.toggle("is-active", nextKeys.has(key));
			currentKeys = nextKeys;
		}
		if (root.isConnected) rafId = requestAnimationFrame(syncActive);
	};

	queueMicrotask(() => {
		if (!root.isConnected) return;
		rafId = requestAnimationFrame(syncActive);
	});

	(root as unknown as { _cleanup?: () => void })._cleanup = () => {
		if (rafId) cancelAnimationFrame(rafId);
	};
	return root;
}