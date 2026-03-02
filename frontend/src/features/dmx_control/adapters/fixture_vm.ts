import type { FixtureState } from "../../../shared/transport/protocol.ts";

export type FixtureVM = {
  id: string;
  name: string;
  type: string;
  armed: boolean;
  hasRgb: boolean;
  hasPanTilt: boolean;
};

export function toFixtureVM(fx: FixtureState): FixtureVM {
  const type = fx.type ?? "unknown";
  const name = fx.name ?? fx.id;
  const armed = !!fx.armed;

  // Presentation mapping (not business logic). Prefer backend-provided capabilities.
  const caps = fx.capabilities ?? {};
  const hasRgb = Boolean((caps as any).rgb) || type === "rgb";
  const hasPanTilt = Boolean((caps as any).pan_tilt) || type === "moving_head";

  return { id: fx.id, name, type, armed, hasRgb, hasPanTilt };
}
