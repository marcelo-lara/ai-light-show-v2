import type { AnalyzerProgress, AnalyzerQueueItem, AnalyzerTaskType } from "../../shared/transport/protocol.ts";

function taskTypeEntry(taskType: string, taskTypes: AnalyzerTaskType[] | null | undefined): AnalyzerTaskType | undefined {
	return taskTypes?.find((option) => option.value === taskType);
}

export function analyzerTaskLabel(taskType: string, taskTypes: AnalyzerTaskType[] | null | undefined): string {
	return taskTypeEntry(taskType, taskTypes)?.label ?? taskType;
}

export function analyzerTaskDescription(taskType: string, taskTypes: AnalyzerTaskType[] | null | undefined): string {
	return taskTypeEntry(taskType, taskTypes)?.description ?? "";
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