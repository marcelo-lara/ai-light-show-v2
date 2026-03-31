import { Button } from "../../../shared/components/controls/Button.ts";
import { Dropdown } from "../../../shared/components/controls/Dropdown.ts";
import { Card } from "../../../shared/components/layout/Card.ts";
import { List } from "../../../shared/components/layout/List.ts";
import { getBackendStore, subscribeBackendStore } from "../../../shared/state/backend_state.ts";
import type { AnalyzerQueueItem } from "../../../shared/transport/protocol.ts";
import { analyzerItemDetail, analyzerProgressLabel, ANALYZER_TASK_OPTIONS, analyzerTaskLabel } from "../analyzer_queue_models.ts";
import { enqueueAnalyzerItem, executeAllAnalyzerItems, executeAnalyzerItem, removeAllAnalyzerItems, removeAnalyzerItem } from "../song_analysis_intents.ts";

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

function renderItemRow(item: AnalyzerQueueItem): HTMLElement {
	const main = document.createElement("div");
	main.className = "analyzer-queue-row-main";
	main.append(
		createText("analyzer-queue-row-title", analyzerTaskLabel(item.task_type)),
		createText("analyzer-queue-row-detail", `${item.status}: ${analyzerItemDetail(item)}`),
	);
	const progress = analyzerProgressLabel(item.progress);
	if (progress) main.append(createText("analyzer-queue-row-detail analyzer-queue-row-progress", progress));
	const actions = document.createElement("div");
	if (item.status === "queued") {
		actions.append(Button({ caption: "Run", state: "primary", bindings: { onClick: () => executeAnalyzerItem(item.item_id) } }));
	}
	if (item.status !== "running") {
		actions.append(Button({ caption: "Remove", bindings: { onClick: () => removeAnalyzerItem(item.item_id) } }));
	}
	return List({ className: "analyzer-queue-row", content: main, actions, isActive: item.status === "running" });
}

export function AnalyzerQueuePanel(): HTMLElement {
	let selectedTask = ANALYZER_TASK_OPTIONS[0]?.value ?? "generate-md";
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
	const dropdown = Dropdown({
		label: "Action",
		value: selectedTask,
		options: ANALYZER_TASK_OPTIONS,
		onChange: (value) => {
			selectedTask = value;
		},
	});
	const footerActions = document.createElement("div");
	footerActions.className = "song-analysis-footer-actions";
	const addButton = Button({ caption: "Add to queue", state: "primary" });
	const runAllButton = Button({ caption: "Run all" });
	const removeAllButton = Button({ caption: "Remove All" });
	footerActions.append(addButton, runAllButton, removeAllButton);
	footer.append(dropdown.root, footerActions);
	content.append(header, body, footer);

	const render = () => {
		body.replaceChildren();
		const state = getBackendStore().state;
		const analyzer = state.analyzer ?? {};
		const items = Array.isArray(analyzer.items) ? analyzer.items : [];
		const summary = typeof analyzer.summary === "object" && analyzer.summary ? analyzer.summary as Record<string, unknown> : undefined;
		const currentSong = state.song?.filename ?? "";
		const queuedCount = summaryCount(summary, "queued");
		const runningCount = summaryCount(summary, "running");
		const removableCount = items.filter((item) => item.status !== "running").length;
		meta.textContent = analyzer.playback_locked ? "playback locked" : analyzer.polling ? "polling" : "idle";
		if (!items.length) {
			body.append(createText("analyzer-queue-empty", analyzer.available === false ? "Analyzer unavailable." : "Queue is empty."));
		} else {
			for (const item of items) body.append(renderItemRow(item));
		}
		addButton.disabled = !currentSong || analyzer.playback_locked === true;
		addButton.title = !currentSong ? "Load a song first" : analyzer.playback_locked === true ? "Playback is running" : "Add task to queue";
		addButton.onclick = () => enqueueAnalyzerItem(selectedTask, currentSong);
		runAllButton.disabled = queuedCount === 0 || analyzer.playback_locked === true;
		runAllButton.title = runningCount > 0 ? "Worker already active" : queuedCount === 0 ? "No queued items" : "Run all queued items";
		runAllButton.onclick = () => executeAllAnalyzerItems();
		removeAllButton.disabled = removableCount === 0 || analyzer.playback_locked === true;
		removeAllButton.title = removableCount === 0 ? "No removable items" : analyzer.playback_locked === true ? "Playback is running" : "Remove all non-running items";
		removeAllButton.onclick = () => removeAllAnalyzerItems();
	};

	const unsubscribeBackend = subscribeBackendStore(render);
	render();
	const card = Card(content, { variant: "outlined" });
	(card as unknown as { _cleanup?: () => void })._cleanup = unsubscribeBackend;
	return card;
}