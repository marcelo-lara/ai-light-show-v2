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

export function createHumanHint(payload: {
	start_time: number;
	end_time: number;
	title: string;
	summary: string;
	lighting_hint: string;
}) {
	wsSend({
		type: "intent",
		req_id: makeId(),
		name: "song.hints.create",
		payload,
	});
}

export function updateHumanHint(id: string, patch: {
	start_time: number;
	end_time: number;
	title: string;
	summary: string;
	lighting_hint: string;
}) {
	wsSend({
		type: "intent",
		req_id: makeId(),
		name: "song.hints.update",
		payload: { id, patch },
	});
}

export function deleteHumanHint(id: string) {
	wsSend({
		type: "intent",
		req_id: makeId(),
		name: "song.hints.delete",
		payload: { id },
	});
}