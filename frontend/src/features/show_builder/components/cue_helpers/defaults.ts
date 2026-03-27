import type { CueHelperDefinition, CueHelperParameterDefinition } from "../../../../shared/transport/protocol.ts";

function getParamDefault(param: CueHelperParameterDefinition, playbackTimeMs: number): unknown {
	if (param.name === "start_time_ms") {
		return playbackTimeMs;
	}
	if (param.default !== undefined) {
		return param.default;
	}
	if (param.type === "select") {
		return param.options?.[0]?.value ?? "";
	}
	if (param.type === "text") {
		return "";
	}
	return 0;
}

export function hydrateCueHelperParams(
	helper: CueHelperDefinition | undefined,
	current: Record<string, unknown>,
	playbackTimeMs: number,
): Record<string, unknown> {
	if (!helper) {
		return {};
	}

	const next: Record<string, unknown> = {};
	for (const param of helper.parameters ?? []) {
		next[param.name] = current[param.name] ?? getParamDefault(param, playbackTimeMs);
	}
	return next;
}