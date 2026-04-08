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