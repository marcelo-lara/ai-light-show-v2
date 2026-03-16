import type { IntentMsg } from "../../shared/transport/protocol.ts";
import { getBackendStore } from "../../shared/state/backend_state.ts";
import { makeId } from "../../shared/utils/id.ts";

const CUE_TIME_MERGE_WINDOW_SECONDS = 0.05;

function wsSend(msg: IntentMsg) {
	const ws = (globalThis as unknown as { __WS_CLIENT__?: { send: (msg: IntentMsg) => void } }).__WS_CLIENT__;
	if (!ws) return;
	ws.send(msg);
}

export function addCue(
	time: number,
	fixtureId: string,
	effect: string,
	duration: number,
	data: Record<string, unknown> = {},
) {
	const cues = getBackendStore().state.cues ?? [];
	let nearestIndex = -1;
	let nearestDelta = Number.POSITIVE_INFINITY;

	for (let index = 0; index < cues.length; index += 1) {
		const cue = cues[index];
		if (cue.fixture_id !== fixtureId) continue;
		const delta = Math.abs(cue.time - time);
		if (delta <= CUE_TIME_MERGE_WINDOW_SECONDS && delta < nearestDelta) {
			nearestDelta = delta;
			nearestIndex = index;
		}
	}

	if (nearestIndex >= 0) {
		updateCue(nearestIndex, {
			effect,
			duration,
			data,
		});
		return;
	}

	wsSend({
		type: "intent",
		req_id: makeId(),
		name: "cue.add",
		payload: {
			time,
			fixture_id: fixtureId,
			effect,
			duration,
			data,
		},
	});
}

export function updateCue(index: number, patch: Record<string, unknown>) {
	wsSend({
		type: "intent",
		req_id: makeId(),
		name: "cue.update",
		payload: {
			index,
			patch,
		},
	});
}

export function deleteCue(index: number) {
	wsSend({
		type: "intent",
		req_id: makeId(),
		name: "cue.delete",
		payload: {
			index,
		},
	});
}

export function clearCues(fromTime = 0, toTime?: number) {
	const payload: Record<string, unknown> = {
		from_time: fromTime,
	};
	if (typeof toTime === "number" && Number.isFinite(toTime)) {
		payload.to_time = toTime;
	}
	wsSend({
		type: "intent",
		req_id: makeId(),
		name: "cue.clear",
		payload,
	});
}

export function applyCueHelper(helperId: string) {
	wsSend({
		type: "intent",
		req_id: makeId(),
		name: "cue.apply_helper",
		payload: {
			helper_id: helperId,
		},
	});
}

export function applyChaser(chaserName: string, startTimeMs = 0, repetitions?: number) {
	const payload: Record<string, unknown> = {
		chaser_name: chaserName,
		start_time_ms: Math.max(0, Math.round(startTimeMs)),
	};
	if (typeof repetitions === "number" && Number.isFinite(repetitions)) {
		payload.repetitions = Math.max(1, Math.floor(repetitions));
	}
	wsSend({
		type: "intent",
		req_id: makeId(),
		name: "chaser.apply",
		payload,
	});
}

export function startChaser(chaserName: string, startTimeMs = 0, repetitions?: number) {
	const payload: Record<string, unknown> = {
		chaser_name: chaserName,
		start_time_ms: Math.max(0, Math.round(startTimeMs)),
	};
	if (typeof repetitions === "number" && Number.isFinite(repetitions)) {
		payload.repetitions = Math.max(1, Math.floor(repetitions));
	}
	wsSend({
		type: "intent",
		req_id: makeId(),
		name: "chaser.start",
		payload,
	});
}

export function stopChaser(instanceId: string) {
	wsSend({
		type: "intent",
		req_id: makeId(),
		name: "chaser.stop",
		payload: {
			instance_id: instanceId,
		},
	});
}

export function listChasers() {
	wsSend({
		type: "intent",
		req_id: makeId(),
		name: "chaser.list",
		payload: {},
	});
}
