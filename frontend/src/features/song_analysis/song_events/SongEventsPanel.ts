import { Card } from "../../../shared/components/layout/Card.ts";
import { List } from "../../../shared/components/layout/List.ts";
import { getSongPlayerTimeMs } from "../../../shared/state/song_player_time.ts";
import { selectPlayback } from "../../../shared/state/selectors.ts";
import { transportJumpToTime } from "../../../shared/transport/transport_intents.ts";
import { SongEvents } from "./SongEvents.ts";

const ACTIVE_SCROLL_PADDING_PX = 12;

function formatTime(value: number): string {
	return Number.isFinite(value) ? value.toFixed(3) : "0.000";
}

function formatAmount(value: number): string {
	return Number.isFinite(value) ? value.toFixed(3) : "0.000";
}

function text(className: string, value: string): HTMLParagraphElement {
	const node = document.createElement("p");
	node.className = className;
	node.textContent = value;
	return node;
}

function metaLine(label: string, value: string): HTMLSpanElement {
	const node = document.createElement("span");
	node.className = "song-events-row-meta-item";
	node.textContent = `${label}: ${value}`;
	return node;
}

function buildRow(event: SongEvents["items"][number], isActive: boolean): HTMLElement {
	const main = document.createElement("div");
	main.className = "song-events-row-main";

	const top = document.createElement("div");
	top.className = "song-events-row-top";
	top.append(
		text("song-events-row-type", event.type),
		text("song-events-row-time", `${formatTime(event.startTime)} - ${formatTime(event.endTime)}`),
	);

	const section = text(
		"song-events-row-section muted",
		event.sectionName ? `${event.sectionName} (${event.sectionId})` : event.sectionId || "Unscoped event",
	);
	const summary = text("song-events-row-summary", event.summary || "No summary available.");
	const details = document.createElement("div");
	details.className = "song-events-row-meta muted";
	details.append(
		metaLine("confidence", formatAmount(event.confidence)),
		metaLine("intensity", formatAmount(event.intensity)),
		metaLine("source", event.provenance || "unknown"),
		metaLine("creator", event.createdBy || "unknown"),
	);

	main.append(top, section, summary, details);
	if (event.evidenceSummary) main.append(text("song-events-row-copy muted", event.evidenceSummary));
	if (event.lightingHint) main.append(text("song-events-row-copy muted", event.lightingHint));

	return List({
		className: "song-events-row",
		content: main,
		isActive,
		onSelect: () => transportJumpToTime(event.startTime * 1000),
		title: event.id,
		dataset: { eventId: event.id },
	});
}

export function SongEventsPanel(events: SongEvents): HTMLElement {
	const content = document.createElement("div");
	content.className = "song-events-panel";

	const header = document.createElement("div");
	header.className = "song-events-header";
	const title = text("song-events-title", "Song Events");
	const meta = text("song-events-meta muted", `${events.items.length} events`);
	header.append(title, meta);

	const body = document.createElement("div");
	body.className = "song-events-body song-events-list o-list";
	content.append(header, body);

	if (!events.items.length) {
		body.append(text("song-events-empty muted", "No song events available for current song."));
		return Card(content, { variant: "outlined" });
	}

	const playback = selectPlayback();
	const initialTimeMs = Math.max(playback.time_ms, getSongPlayerTimeMs());
	let currentIndex = events.activeIndex(initialTimeMs);
	const rows = events.items.map((event, index) => buildRow(event, index === currentIndex));
	body.append(...rows);

	let rafId = 0;

	const scrollActiveIntoView = (index: number) => {
		if (index < 0) return;
		const row = rows[index];
		if (!row) return;
		const containerRect = body.getBoundingClientRect();
		const rowRect = row.getBoundingClientRect();
		const topEdge = containerRect.top + ACTIVE_SCROLL_PADDING_PX;
		const bottomEdge = containerRect.bottom - ACTIVE_SCROLL_PADDING_PX;
		if (rowRect.top < topEdge || rowRect.bottom > bottomEdge) {
			row.scrollIntoView({ block: "nearest", inline: "nearest" });
		}
	};

	const syncActive = () => {
		const nextIndex = events.activeIndex(getSongPlayerTimeMs());
		if (nextIndex !== currentIndex) {
			if (currentIndex >= 0) rows[currentIndex]?.classList.remove("is-active");
			if (nextIndex >= 0) rows[nextIndex]?.classList.add("is-active");
			scrollActiveIntoView(nextIndex);
			currentIndex = nextIndex;
		}
		if (content.isConnected) rafId = requestAnimationFrame(syncActive);
	};

	queueMicrotask(() => {
		if (!content.isConnected) return;
		scrollActiveIntoView(currentIndex);
		rafId = requestAnimationFrame(syncActive);
	});

	const card = Card(content, { variant: "outlined" });
	(card as unknown as { _cleanup?: () => void })._cleanup = () => {
		if (rafId) cancelAnimationFrame(rafId);
	};
	return card;
}