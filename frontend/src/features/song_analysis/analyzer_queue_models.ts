import type { AnalyzerProgress, AnalyzerQueueItem } from "../../shared/transport/protocol.ts";

export const ANALYZER_TASK_OPTIONS = [
	{ value: "split-stems", label: "Split Stems" },
	{ value: "beat-finder", label: "Beat Finder" },
	{ value: "essentia-analysis", label: "Essentia Analysis" },
	{ value: "find-song-features", label: "Find Song Features" },
	{ value: "import-moises", label: "Import Moises" },
	{ value: "generate-md", label: "Generate Markdown" },
];

export function analyzerTaskLabel(taskType: string): string {
	return ANALYZER_TASK_OPTIONS.find((option) => option.value === taskType)?.label ?? taskType;
}

export function analyzerProgressLabel(progress: AnalyzerProgress | null | undefined): string {
	if (!progress) return "";
	const stepCurrent = typeof progress.step_current === "number" ? progress.step_current : null;
	const stepTotal = typeof progress.step_total === "number" ? progress.step_total : null;
	const stage = typeof progress.stage === "string" ? progress.stage : "";
	const message = typeof progress.message === "string" ? progress.message : "";
	if (stepCurrent !== null && stepTotal !== null && stage) return `${stage} ${stepCurrent}/${stepTotal}`;
	return message || stage;
}

export function analyzerItemDetail(item: AnalyzerQueueItem): string {
	if (item.status === "running") return analyzerProgressLabel(item.progress) || "Running";
	if (item.status === "failed") return item.error === "Interrupted before completion" ? "Waiting..." : item.error || "Failed";
	if (item.status === "complete") return item.last_result && item.last_result.ok === true ? "Complete" : "Complete";
	if (item.status === "pending") return "Waiting...";
	return "Queued";
}