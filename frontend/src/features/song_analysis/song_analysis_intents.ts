import type { IntentMsg } from "../../shared/transport/protocol.ts";
import { makeId } from "../../shared/utils/id.ts";

function wsSend(msg: IntentMsg) {
	const ws = (globalThis as unknown as { __WS_CLIENT__?: { send: (msg: IntentMsg) => void } }).__WS_CLIENT__;
	if (!ws) return;
	ws.send(msg);
}

export function requestSongList() {
	wsSend({
		type: "intent",
		req_id: makeId(),
		name: "song.list",
		payload: {},
	});
}

export function loadSong(filename: string) {
	wsSend({
		type: "intent",
		req_id: makeId(),
		name: "song.load",
		payload: { filename },
	});
}

export function enqueueAnalyzerItem(taskType: string, filename: string) {
	wsSend({
		type: "intent",
		req_id: makeId(),
		name: "analyzer.enqueue",
		payload: { task_type: taskType, filename },
	});
}

export function removeAnalyzerItem(itemId: string) {
	wsSend({
		type: "intent",
		req_id: makeId(),
		name: "analyzer.remove",
		payload: { item_id: itemId },
	});
}

export function removeAllAnalyzerItems() {
	wsSend({
		type: "intent",
		req_id: makeId(),
		name: "analyzer.remove_all",
		payload: {},
	});
}

export function executeAnalyzerItem(itemId: string) {
	wsSend({
		type: "intent",
		req_id: makeId(),
		name: "analyzer.execute",
		payload: { item_id: itemId },
	});
}

export function executeAllAnalyzerItems() {
	wsSend({
		type: "intent",
		req_id: makeId(),
		name: "analyzer.execute_all",
		payload: {},
	});
}