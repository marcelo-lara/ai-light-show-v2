import type { IntentMsg } from "../../shared/transport/protocol.ts";
import { makeId } from "../../shared/utils/id.ts";

function wsSend(msg: IntentMsg) {
  const ws = (globalThis as any).__WS_CLIENT__;
  if (!ws) return;
  ws.send(msg);
}

function reqId() {
  return makeId();
}

export function setArm(fixtureId: string, armed: boolean) {
  wsSend({
    type: "intent",
    req_id: reqId(),
    name: "fixture.set_arm",
    payload: { fixture_id: fixtureId, armed },
  });
}

export function setFixtureValues(fixtureId: string, values: Record<string, number | string>) {
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

export function updatePoiFixtureTarget(poiId: string, fixtureId: string, pan: number, tilt: number) {
  wsSend({
    type: "intent",
    req_id: reqId(),
    name: "poi.update_fixture_target",
    payload: {
      poi_id: poiId,
      fixture_id: fixtureId,
      pan,
      tilt,
    },
  });
}
