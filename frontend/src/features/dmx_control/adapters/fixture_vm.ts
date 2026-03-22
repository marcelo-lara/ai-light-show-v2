import type { FixtureState, MetaChannel } from "../../../shared/transport/protocol.ts";

export type FixtureVM = {
  id: string;
  name: string;
  type: string;
  armed: boolean;
  hasRgb: boolean;
  hasPanTilt: boolean;
  values: Record<string, number | string>;
  metaChannels: Record<string, MetaChannel>;
  mappings: Record<string, Record<string, number | string>>;
  supportedEffects: string[];
};

export function toFixtureVM(fx: FixtureState): FixtureVM {
  const type = fx.type ?? "unknown";
  const name = fx.name ?? fx.id;
  const armed = !!fx.armed;
  const values = fx.values ?? {};
  const metaChannels = fx.meta_channels ?? {};
  const mappings = fx.mappings ?? {};
  const supportedEffects = fx.supported_effects ?? [];

  // Presentation mapping (not business logic). Prefer backend-provided capabilities.
  const caps = fx.capabilities ?? {};
  const hasRgb = Boolean(caps.rgb) || type === "rgb";
  const hasPanTilt = Boolean(caps.pan_tilt) || type === "moving_head";

  return { id: fx.id, name, type, armed, hasRgb, hasPanTilt, values, metaChannels, mappings, supportedEffects };
}
