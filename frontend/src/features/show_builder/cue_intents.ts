import type { IntentMsg } from "../../shared/transport/protocol.ts";
import { makeId } from "../../shared/utils/id.ts";

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
