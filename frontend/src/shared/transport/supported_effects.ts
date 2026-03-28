import type { SupportedEffectDescriptor } from "./protocol.ts";

export type SupportedEffectOption = {
	id: string;
	label: string;
};

function readEffectId(effect: SupportedEffectDescriptor): string {
	return effect.id.trim();
}

export function getSupportedEffectIds(supportedEffects?: SupportedEffectDescriptor[]): string[] {
	const ids: string[] = [];
	const seen = new Set<string>();
	for (const effect of supportedEffects ?? []) {
		const id = readEffectId(effect);
		if (!id || seen.has(id)) continue;
		seen.add(id);
		ids.push(id);
	}
	return ids;
}

export function getSupportedEffectOptions(supportedEffects?: SupportedEffectDescriptor[]): SupportedEffectOption[] {
	const options: SupportedEffectOption[] = [];
	const seen = new Set<string>();
	for (const effect of supportedEffects ?? []) {
		const id = readEffectId(effect);
		if (!id || seen.has(id)) continue;
		seen.add(id);
		options.push({
			id,
			label: effect.name.trim() || id,
		});
	}
	return options;
}