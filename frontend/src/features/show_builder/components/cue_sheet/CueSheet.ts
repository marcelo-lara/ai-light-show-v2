import { Card } from "../../../../shared/components/layout/Card.ts";
import { Button } from "../../../../shared/components/controls/Button.ts";
import { ConfirmCancelPrompt } from "../../../../shared/components/feedback/ConfirmCancelPrompt.ts";
import type { CueEntry } from "../../../../shared/transport/protocol.ts";
import { getBackendStore, subscribeBackendStore } from "../../../../shared/state/backend_state.ts";
import { deleteCue, previewChaser, reloadCueSheet } from "../../cue_intents.ts";
import { previewEffect } from "../../../dmx_control/fixture_intents.ts";
import { transportJumpToTime } from "../../../../shared/transport/transport_intents.ts";
import {
	formatCueLabel,
	getChaserById,
	getCueRepetitions,
	isChaserCue,
	isEffectCue,
} from "../../cue_utils.ts";
import { cueSignature, findCurrentCueTime, formatCueTime } from "./format.ts";
import { createCueRow, createEmptyCueSheetState } from "./row.ts";

export function CueSheet(): HTMLElement {
	const content = document.createElement("div");
	content.className = "cue-sheet-body";

	const header = document.createElement("div");
	header.className = "cue-sheet-header";
	const title = document.createElement("div");
	title.className = "cue-sheet-header-title";
	const eyebrow = document.createElement("p");
	eyebrow.className = "cue-sheet-header-eyebrow muted";
	eyebrow.textContent = "Cue Sheet";

	title.append(eyebrow);
	const headerMeta = document.createElement("div");
	headerMeta.className = "cue-sheet-header-meta";
	const reloadButton = Button({
		caption: "Reload",
		bindings: {
			title: "Reload cue sheet from disk",
			onClick: () => {
				reloadCueSheet();
			},
		},
	});
	const count = document.createElement("span");
	count.className = "cue-sheet-header-count";
	headerMeta.append(reloadButton, count);
	header.append(title, headerMeta);

	const listContainer = document.createElement("div");
	listContainer.className = "cue-sheet-list o-list";
	content.append(header, listContainer);

	let lastCueSignature = "";
	let lastCurrentTime: number | null = null;

	function getCues(): CueEntry[] {
		return getBackendStore().state.cues ?? [];
	}

	function getTimeMs(): number {
		return getBackendStore().state.playback?.time_ms ?? 0;
	}

	function getDeletePromptMessage(cue: CueEntry): string {
		if (isChaserCue(cue)) {
			const chasers = getBackendStore().state.chasers ?? [];
			const chaser = getChaserById(chasers, cue.chaser_id);
			const name = chaser?.name ?? formatCueLabel(cue.chaser_id);
			return `Delete Chaser '${name}' at ${formatCueTime(cue.time)} from the Cue?`;
		}
		const effectName = formatCueLabel(cue.effect);
		return `Delete Effect '${effectName}' at ${formatCueTime(cue.time)} from the Cue?`;
	}

	async function confirmDeleteCue(index: number, cue: CueEntry): Promise<void> {
		const confirmed = await ConfirmCancelPrompt({
			title: "Delete cue",
			message: getDeletePromptMessage(cue),
			confirmLabel: "Delete",
			cancelLabel: "Cancel",
		});
		if (!confirmed) return;
		deleteCue(index);
	}

	function renderList(): void {
		const state = getBackendStore().state;
		const cues = getCues();
		const currentTime = findCurrentCueTime(cues, getTimeMs());
		const signature = cueSignature(cues);
		reloadButton.disabled = Boolean(state.system?.edit_lock) || !state.song?.filename;
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
							if (isEffectCue(cue)) {
								previewEffect(cue.fixture_id, cue.effect, cue.duration * 1000, cue.data ?? {});
								return;
							}
							if (isChaserCue(cue)) {
								previewChaser(cue.chaser_id, cue.time * 1000, getCueRepetitions(cue));
							}
						},
						onDelete: () => {
							void confirmDeleteCue(index, cue);
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
