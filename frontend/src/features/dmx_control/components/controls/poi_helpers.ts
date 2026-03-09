import type { Poi } from "../../../../shared/transport/protocol.ts";

export type FixturePoiTarget = {
	pan: number;
	tilt: number;
};

export type PoiWithFixtureTargets = Poi & {
	fixtures?: Record<string, FixturePoiTarget>;
};

export function normalizePois(rawPois: Poi[] | undefined): PoiWithFixtureTargets[] {
	return (rawPois ?? []) as PoiWithFixtureTargets[];
}

export function hasFixtureTargetDiff(
	target: FixturePoiTarget | undefined,
	currentPan: number,
	currentTilt: number,
): boolean {
	if (!target) return true;
	return target.pan !== currentPan || target.tilt !== currentTilt;
}
