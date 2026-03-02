import type { IntentMsg } from "../../shared/transport/protocol.ts";

function wsSend(msg: IntentMsg) {
  const ws = (globalThis as any).__WS_CLIENT__;
  if (!ws) return;
  ws.send(msg);
}

function reqId() {
  return crypto.randomUUID();
}

export function setArm(fixtureId: string, armed: boolean) {
  wsSend({
    type: "intent",
    req_id: reqId(),
    name: "fixture.set_arm",
    payload: { fixture_id: fixtureId, armed },
  });
}

export function setFixtureValues(fixtureId: string, values: Record<string, number>) {
  wsSend({
    type: "intent",
    req_id: reqId(),
    name: "fixture.set_values",
    payload: { fixture_id: fixtureId, values },
  });
}

export function previewEffect(
  fixtureId: string,
  effectId: string,
  durationMs: number,
  params: Record<string, unknown> = {},
) {
  wsSend({
    type: "intent",
    req_id: reqId(),
    name: "fixture.preview_effect",
    payload: { fixture_id: fixtureId, effect_id: effectId, duration_ms: durationMs, params },
  });
}
