import { Button } from "../../../shared/components/controls/Button.ts";
import { Toggle } from "../../../shared/components/controls/Toggle.ts";
import { Card } from "../../../shared/components/layout/Card.ts";
import { List } from "../../../shared/components/layout/List.ts";
import { getBackendStore, subscribeBackendStore } from "../../../shared/state/backend_state.ts";
import type { AnalyzerQueueItem, AnalyzerTaskType } from "../../../shared/transport/protocol.ts";
import { analyzerItemDetail, analyzerItemProgressPercent, analyzerItemProgressTone, analyzerProgressLabel, analyzerTaskDescription, analyzerTaskLabel } from "./models.ts";

function createText(className: string, text: string): HTMLSpanElement {
	const node = document.createElement("span");
	node.className = className;
	node.textContent = text;
	return node;
}

function summaryCount(summary: Record<string, unknown> | undefined, key: string): number {
	const value = summary?.[key];
	return typeof value === "number" ? value : 0;
}

function isAnalyzerTaskType(value: unknown): value is AnalyzerTaskType {
	return Boolean(
		value &&
			typeof value === "object" &&
			typeof (value as AnalyzerTaskType).value === "string" &&
			typeof (value as AnalyzerTaskType).label === "string" &&
			typeof (value as AnalyzerTaskType).description === "string",
	);
}

function setButtonCaption(button: HTMLButtonElement, caption: string): void {
	const label = button.querySelector(".btn-caption");
	if (label) label.textContent = caption;
	button.title = caption;
	button.setAttribute("aria-label", caption);
}

function renderItemRow(item: AnalyzerQueueItem, taskTypes: AnalyzerTaskType[]): HTMLElement {
	const main = document.createElement("div");
	main.className = "analyzer-queue-row-main";
	main.append(
		createText("analyzer-queue-row-title", analyzerTaskLabel(item.task_type, taskTypes)),
		createText("analyzer-queue-row-detail", `${item.status}: ${analyzerItemDetail(item)}`),
	);
	const progress = analyzerProgressLabel(item.progress);
	if (progress) main.append(createText("analyzer-queue-row-detail analyzer-queue-row-progress", progress));
	const progressTrack = document.createElement("div");
	progressTrack.className = "analyzer-queue-row-status";
	const progressFill = document.createElement("div");
	progressFill.className = `analyzer-queue-row-status-fill is-${analyzerItemProgressTone(item)}`;
	progressFill.style.width = `${analyzerItemProgressPercent(item)}%`;
	progressTrack.append(progressFill);
	return List({
		className: `analyzer-queue-row ${item.status}`,
		content: [main, progressTrack],
	});
}

export function AnalyzerQueuePanel(): HTMLElement {
	let selectedTasks = new Set<string>();
	let isExpanded = false;
	const content = document.createElement("div");
	content.className = "analyzer-queue-panel";
	const header = document.createElement("div");
	header.className = "analyzer-queue-header";
	const title = createText("analyzer-queue-title", "Analyzer Queue");
	const meta = createText("analyzer-queue-meta", "idle");
	header.append(title, meta);
	const body = document.createElement("div");
	body.className = "analyzer-queue-body analyzer-queue-list o-list";
	const footer = document.createElement("div");
	footer.className = "song-analysis-footer";
	const actionsToggle = Button({ caption: "Analyze Song ⌃" });
	const actionsPanel = document.createElement("div");
	actionsPanel.className = "analyzer-queue-actions";
	actionsPanel.hidden = true;
	const taskList = document.createElement("div");
	taskList.className = "analyzer-queue-task-list";
	const footerActions = document.createElement("div");
	footerActions.className = "song-analysis-footer-actions";
	const fullAnalysisButton = Button({ caption: "Run Full Analysis", state: "primary" });
	const addButton = Button({ caption: "Add Selected" });
	const runAllButton = Button({ caption: "Run all" });
	const removeAllButton = Button({ caption: "Remove All" });
	actionsPanel.append(fullAnalysisButton, taskList, footerActions);
	footerActions.append(addButton, runAllButton, removeAllButton);
	footer.append(actionsToggle, actionsPanel);
	content.append(header, body, footer);

	const render = () => {
		body.replaceChildren();
		taskList.replaceChildren();
		const state = getBackendStore().state;
		const analyzer = state.analyzer ?? {};
		const taskTypes = Array.isArray(analyzer.task_types) ? analyzer.task_types.filter(isAnalyzerTaskType) : [];
		const items = Array.isArray(analyzer.items) ? analyzer.items : [];
		const summary = typeof analyzer.summary === "object" && analyzer.summary ? analyzer.summary as Record<string, unknown> : undefined;
		const currentSong = state.song?.filename ?? "";
		const queuedCount = summaryCount(summary, "queued");
		const pendingCount = summaryCount(summary, "pending");
		const runningCount = summaryCount(summary, "running");
		const removableCount = items.filter((item) => item.status !== "running").length;
		const taskValues = new Set(taskTypes.map((item) => item.value));
		selectedTasks = new Set([...selectedTasks].filter((taskType) => taskValues.has(taskType)));
		meta.textContent = analyzer.available === false ? "unavailable" : analyzer.playback_locked ? "playback locked" : analyzer.polling ? "polling" : "idle";
		setButtonCaption(actionsToggle, isExpanded ? "Analyze Song ⌄" : "Analyze Song ⌃");
		actionsPanel.hidden = !isExpanded;
		if (!items.length) {
			body.append(createText("analyzer-queue-empty", analyzer.available === false ? "Analyzer unavailable." : "Queue is empty."));
		} else {
			for (const item of items) body.append(renderItemRow(item, taskTypes));
		}
		if (!taskTypes.length) {
			taskList.append(createText("analyzer-queue-empty", analyzer.available === false ? "Task catalog unavailable." : "No analyzer tasks available."));
		} else {
			for (const taskType of taskTypes) {
				const row = document.createElement("div");
				row.className = "analyzer-queue-task-item";
				const description = analyzerTaskDescription(taskType.value, taskTypes);
				const toggle = Toggle({
					label: taskType.label,
					checked: selectedTasks.has(taskType.value),
					description,
					onChange: (checked) => {
						if (checked) selectedTasks.add(taskType.value);
						else selectedTasks.delete(taskType.value);
						render();
					},
				});
				row.append(toggle.root);
				taskList.append(row);
			}
		}
		actionsToggle.onclick = () => {
			isExpanded = !isExpanded;
			render();
		};
		fullAnalysisButton.disabled = !currentSong || analyzer.available === false || analyzer.playback_locked === true;
		fullAnalysisButton.title = !currentSong
			? "Load a song first"
			: analyzer.available === false
				? "Analyzer unavailable"
				: analyzer.playback_locked === true
					? "Playback is running"
					: "Queue the analyzer full-artifact playlist and start it immediately";
		addButton.disabled = !currentSong || analyzer.available === false || analyzer.playback_locked === true || selectedTasks.size === 0;
		addButton.title = !currentSong
			? "Load a song first"
			: analyzer.available === false
				? "Analyzer unavailable"
				: analyzer.playback_locked === true
					? "Playback is running"
					: selectedTasks.size === 0
						? "Select at least one task"
						: "Add selected tasks to queue";
		runAllButton.disabled = queuedCount === 0 || analyzer.available === false || analyzer.playback_locked === true;
		runAllButton.title = runningCount > 0 || pendingCount > 0 ? "Worker already active" : queuedCount === 0 ? "No queued items" : "Run all queued items";
		removeAllButton.disabled = removableCount === 0 || analyzer.available === false || analyzer.playback_locked === true;
		removeAllButton.title = removableCount === 0 ? "No removable items" : analyzer.playback_locked === true ? "Playback is running" : analyzer.available === false ? "Analyzer unavailable" : "Remove all non-running items";
	};

	const unsubscribeBackend = subscribeBackendStore(render);
	render();
	const card = Card(content, { variant: "outlined" });
	(card as unknown as { _cleanup?: () => void })._cleanup = unsubscribeBackend;
	return card;
}