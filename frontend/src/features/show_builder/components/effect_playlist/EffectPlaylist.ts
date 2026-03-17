import { Card } from "../../../../shared/components/layout/Card.ts";
import { ConfirmCancelPrompt } from "../../../../shared/components/feedback/ConfirmCancelPrompt.ts";
import type { CueEntry } from "../../../../shared/transport/protocol.ts";
import { getBackendStore, subscribeBackendStore } from "../../../../shared/state/backend_state.ts";
import { deleteCue } from "../../cue_intents.ts";
import { previewEffect } from "../../../dmx_control/fixture_intents.ts";
import { transportJumpToTime } from "../../../../shared/transport/transport_intents.ts";
import { cueSignature, findCurrentCueTime } from "./format.ts";
import { createCueRow, createEmptyCueSheetState } from "../cue_sheet/row.ts";

export function EffectPlaylist(): HTMLElement {
	const content = document.createElement("div");
	content.className = "cue-sheet-body";

	const header = document.createElement("div");
	header.className = "cue-sheet-header";
	const title = document.createElement("div");
	title.className = "cue-sheet-header__title";
	const eyebrow = document.createElement("p");
	eyebrow.className = "cue-sheet-header__eyebrow muted";
	eyebrow.textContent = "Cue Sheet";

	title.append(eyebrow);
	const count = document.createElement("span");
	count.className = "cue-sheet-header__count";
	header.append(title, count);

	const listContainer = document.createElement("div");
	listContainer.className = "cue-sheet-list c-list";
	content.append(header, listContainer);

	let lastCueSignature = "";
	let lastCurrentTime: number | null = null;

	function getCues(): CueEntry[] {
		return getBackendStore().state.cues ?? [];
	}

	function getTimeMs(): number {
		return getBackendStore().state.playback?.time_ms ?? 0;
	}

	async function confirmDeleteCue(index: number): Promise<void> {
		const confirmed = await ConfirmCancelPrompt({
			title: "Delete cue",
			message: "This cue will be removed from the playlist.",
			confirmLabel: "Delete",
			cancelLabel: "Cancel",
		});
		if (!confirmed) return;
		deleteCue(index);
	}

	function renderList(): void {
		const cues = getCues();
		const currentTime = findCurrentCueTime(cues, getTimeMs());
		const signature = cueSignature(cues);
		count.textContent = `${cues.length} ${cues.length === 1 ? "cue" : "cues"}`;

		if (signature !== lastCueSignature) {
			lastCueSignature = signature;
			listContainer.querySelectorAll(".cue-sheet-row, .cue-sheet-empty").forEach((node) => node.remove());
			if (cues.length === 0) {
				listContainer.appendChild(createEmptyCueSheetState());
			} else {
				for (const [index, cue] of cues.entries()) {
					listContainer.appendChild(createCueRow(cue, {
						onEdit: () => {
							transportJumpToTime(cue.time * 1000);
							window.dispatchEvent(new CustomEvent("show-builder:cue-edit", {
								detail: { index, cue },
							}));
						},
						onPreview: () => {
							previewEffect(cue.fixture_id, cue.effect, cue.duration * 1000, cue.data ?? {});
						},
						onDelete: () => {
							void confirmDeleteCue(index);
						},
						onSelect: () => {
							transportJumpToTime(cue.time * 1000);
						},
					}));
				}
			}
		}

		if (currentTime !== lastCurrentTime) {
			lastCurrentTime = currentTime;
			const rows = listContainer.querySelectorAll<HTMLElement>(".cue-sheet-row");
			const activeRows: HTMLElement[] = [];
			rows.forEach((row) => {
				const rowTime = Number(row.dataset.time ?? Number.NaN);
				const isCurrent = currentTime !== null && Number.isFinite(rowTime) && Math.abs(rowTime - currentTime) < 1e-6;
				row.classList.toggle("is-active", isCurrent);
				if (isCurrent) activeRows.push(row);
			});
			if (activeRows[0]) {
				activeRows[0].scrollIntoView({ block: "nearest", behavior: "smooth" });
			}
		}
	}

	renderList();
	const unsubscribe = subscribeBackendStore(renderList);
	(content as unknown as { _cleanup: () => void })._cleanup = unsubscribe;
	return Card(content, { variant: "outlined", className: "show-builder-panel" });
}