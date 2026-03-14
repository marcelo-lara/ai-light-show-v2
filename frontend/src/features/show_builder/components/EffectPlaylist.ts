import { Card } from "../../../shared/components/layout/Card.ts";
import type { CueEntry } from "../../../shared/transport/protocol.ts";
import { getBackendStore, subscribeBackendStore } from "../../../shared/state/backend_state.ts";

function formatParams(data: Record<string, unknown>): string {
	const entries = Object.entries(data);
	if (entries.length === 0) return "—";
	return entries
		.slice(0, 3)
		.map(([k, v]) => `${k}:${v}`)
		.join(" ");
}

function findCurrentCueIndex(cues: CueEntry[], timeMs: number): number {
	const timeSec = timeMs / 1000;
	for (let i = cues.length - 1; i >= 0; i--) {
		if (cues[i].time <= timeSec) return i;
	}
	return -1;
}

export function EffectPlaylist(): HTMLElement {
	const content = document.createElement("div");
	content.className = "effect-playlist-body";

	const labels = document.createElement("p");
	labels.className = "effect-playlist-labels mono muted";
	labels.textContent = "time fixture effect duration parameters delete";
	content.appendChild(labels);

	const listContainer = document.createElement("div");
	listContainer.className = "effect-playlist-list";
	content.appendChild(listContainer);

	let lastCueCount = -1;
	let lastCurrentIndex = -1;

	function getCues(): CueEntry[] {
		return getBackendStore().state.cues ?? [];
	}

	function getTimeMs(): number {
		return getBackendStore().state.playback?.time_ms ?? 0;
	}

	function renderList() {
		const cues = getCues();
		const timeMs = getTimeMs();
		const currentIndex = findCurrentCueIndex(cues, timeMs);

		// Only re-render if cues changed
		if (cues.length !== lastCueCount) {
			lastCueCount = cues.length;
			listContainer.innerHTML = "";

			if (cues.length === 0) {
				const empty = document.createElement("p");
				empty.className = "muted";
				empty.textContent = "No cues yet. Add effects above.";
				listContainer.appendChild(empty);
				return;
			}

			for (const cue of cues) {
				const line = document.createElement("div");
				line.className = "effect-playlist-row mono";
				line.dataset.time = String(cue.time);

				const left = document.createElement("span");
				left.textContent = `${cue.time.toFixed(2)} ${cue.fixture_id} ${cue.effect} ${cue.duration.toFixed(1)} ${formatParams(cue.data)}`;

				const del = document.createElement("button");
				del.type = "button";
				del.className = "btn effect-playlist-delete";
				del.textContent = "x";
				// TODO: wire delete to cue.delete intent when implemented

				line.append(left, del);
				listContainer.appendChild(line);
			}
		}

		// Update current highlight
		if (currentIndex !== lastCurrentIndex) {
			lastCurrentIndex = currentIndex;
			const rows = listContainer.querySelectorAll(".effect-playlist-row");
			rows.forEach((row, idx) => {
				row.classList.toggle("is-current", idx === currentIndex);
			});

			// Scroll current into view
			if (currentIndex >= 0 && rows[currentIndex]) {
				rows[currentIndex].scrollIntoView({ block: "nearest", behavior: "smooth" });
			}
		}
	}

	// Initial render
	renderList();

	// Subscribe to state changes
	const unsubscribe = subscribeBackendStore(() => {
		renderList();
	});

	// Cleanup
	(content as unknown as { _cleanup: () => void })._cleanup = unsubscribe;

	return Card(content, { variant: "outlined", className: "show-builder-panel" });
}
