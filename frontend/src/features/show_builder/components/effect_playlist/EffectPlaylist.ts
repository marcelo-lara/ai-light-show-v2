import { Card } from "../../../../shared/components/layout/Card.ts";
import type { CueEntry } from "../../../../shared/transport/protocol.ts";
import { getBackendStore, subscribeBackendStore } from "../../../../shared/state/backend_state.ts";
import { deleteCue } from "../../cue_intents.ts";
import { previewEffect } from "../../../dmx_control/fixture_intents.ts";
import { cueSignature, findCurrentCueIndex } from "./format.ts";
import { createCueRow, createEmptyPlaylistState } from "./row.ts";

export function EffectPlaylist(): HTMLElement {
	const content = document.createElement("div");
	content.className = "effect-playlist-body";

	const header = document.createElement("div");
	header.className = "effect-playlist-header";
	const title = document.createElement("div");
	title.className = "effect-playlist-header__title";
	const eyebrow = document.createElement("p");
	eyebrow.className = "effect-playlist-header__eyebrow muted";
	eyebrow.textContent = "Show flow";
	const heading = document.createElement("h2");
	heading.className = "effect-playlist-header__heading";
	heading.textContent = "Effects Playlist";
	title.append(eyebrow, heading);
	const count = document.createElement("span");
	count.className = "effect-playlist-header__count";
	header.append(title, count);

	const listContainer = document.createElement("div");
	listContainer.className = "effect-playlist-list";
	content.append(header, listContainer);

	let lastCueSignature = "";
	let lastCurrentIndex = -1;

	function getCues(): CueEntry[] {
		return getBackendStore().state.cues ?? [];
	}

	function getTimeMs(): number {
		return getBackendStore().state.playback?.time_ms ?? 0;
	}

	function renderList(): void {
		const cues = getCues();
		const currentIndex = findCurrentCueIndex(cues, getTimeMs());
		const signature = cueSignature(cues);
		count.textContent = `${cues.length} ${cues.length === 1 ? "cue" : "cues"}`;

		if (signature !== lastCueSignature) {
			lastCueSignature = signature;
			listContainer.querySelectorAll(".effect-playlist-row, .effect-playlist-empty").forEach((node) => node.remove());
			if (cues.length === 0) {
				listContainer.appendChild(createEmptyPlaylistState());
			} else {
				for (const [index, cue] of cues.entries()) {
					listContainer.appendChild(createCueRow(cue, {
						onEdit: () => {
							window.dispatchEvent(new CustomEvent("show-builder:cue-edit", {
								detail: { index, cue },
							}));
						},
						onPreview: () => {
							previewEffect(cue.fixture_id, cue.effect, cue.duration * 1000, cue.data ?? {});
						},
						onDelete: () => {
							deleteCue(index);
						},
					}));
				}
			}
		}

		if (currentIndex !== lastCurrentIndex) {
			lastCurrentIndex = currentIndex;
			const rows = listContainer.querySelectorAll<HTMLElement>(".effect-playlist-row");
			rows.forEach((row, index) => row.classList.toggle("is-active", index === currentIndex));
			if (currentIndex >= 0 && rows[currentIndex]) {
				rows[currentIndex].scrollIntoView({ block: "nearest", behavior: "smooth" });
			}
		}
	}

	renderList();
	const unsubscribe = subscribeBackendStore(renderList);
	(content as unknown as { _cleanup: () => void })._cleanup = unsubscribe;
	return Card(content, { variant: "outlined", className: "show-builder-panel" });
}