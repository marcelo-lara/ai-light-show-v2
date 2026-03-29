/**
 * Effect parameter schema definitions for dynamic form generation.
 * Maps effect names to parameter definitions used by the Effect Picker.
 */

export type ParamType = "number" | "range" | "color" | "select" | "poi";

export type ParamDef = {
	name: string;
	label: string;
	type: ParamType;
	default?: number | string;
	min?: number;
	max?: number;
	step?: number;
	options?: string[]; // for select type
};

export type EffectSchema = {
	name: string;
	label: string;
	params: ParamDef[];
	defaultDurationBeats?: number;
	fixtureTypes?: string[]; // restrict to specific fixture types
};

/**
 * Effect schemas by effect name.
 * Keys are lowercase effect names as returned by backend.
 */
export const EFFECT_SCHEMAS: Record<string, EffectSchema | EffectSchema[]> = {
	// Parcan effects
	flash: {
		name: "flash",
		label: "Flash",
		params: [],
		fixtureTypes: ["parcan", "rgb", "moving_head"],
	},
	strobe: {
		name: "strobe",
		label: "Strobe",
		params: [
			{ name: "rate", label: "Rate (Hz)", type: "range", default: 10, min: 1, max: 20, step: 1 },
		],
		fixtureTypes: ["parcan", "rgb", "moving_head"],
	},
	fade_in: [
		{
			name: "fade_in",
			label: "Fade In",
			params: [
				{ name: "red", label: "Red", type: "range", default: 255, min: 0, max: 255, step: 1 },
				{ name: "green", label: "Green", type: "range", default: 255, min: 0, max: 255, step: 1 },
				{ name: "blue", label: "Blue", type: "range", default: 255, min: 0, max: 255, step: 1 },
			],
			fixtureTypes: ["parcan", "rgb"],
		},
		{
			name: "fade_in",
			label: "Fade In",
			params: [
				{ name: "dim", label: "Dimmer", type: "range", default: 255, min: 0, max: 255, step: 1 },
			],
			fixtureTypes: ["moving_head"],
		},
	],
	full: [
		{
			name: "full",
			label: "Full",
			params: [
				{ name: "red", label: "Red", type: "range", default: 255, min: 0, max: 255, step: 1 },
				{ name: "green", label: "Green", type: "range", default: 255, min: 0, max: 255, step: 1 },
				{ name: "blue", label: "Blue", type: "range", default: 255, min: 0, max: 255, step: 1 },
			],
			fixtureTypes: ["parcan", "rgb"],
		},
		{
			name: "full",
			label: "Full",
			params: [],
			fixtureTypes: ["moving_head"],
		},
	],
	// Moving head effects
	orbit: {
		name: "orbit",
		label: "Orbit",
		params: [
			{ name: "subject_POI", label: "Subject POI", type: "poi", default: "" },
			{ name: "start_POI", label: "Start POI", type: "poi", default: "" },
			{ name: "orbits", label: "Orbits", type: "range", default: 1, min: 0, max: 4, step: 0.25 },
			{ name: "easing", label: "Spiral Easing", type: "select", default: "late_focus", options: ["late_focus", "balanced", "linear", "early_focus"] },
		],
		defaultDurationBeats: 2,
		fixtureTypes: ["moving_head"],
	},
	move_to: {
		name: "move_to",
		label: "Move To",
		params: [
			{ name: "pan", label: "Pan", type: "range", default: 32768, min: 0, max: 65535, step: 256 },
			{ name: "tilt", label: "Tilt", type: "range", default: 32768, min: 0, max: 65535, step: 256 },
		],
		fixtureTypes: ["moving_head"],
	},
	move_to_poi: {
		name: "move_to_poi",
		label: "Move To POI",
		params: [
			{ name: "poi", label: "Target POI", type: "poi", default: "" },
		],
		fixtureTypes: ["moving_head"],
	},
	sweep: {
		name: "sweep",
		label: "Sweep",
		params: [
			{ name: "subject_POI", label: "Subject POI", type: "poi", default: "" },
			{ name: "start_POI", label: "Start POI", type: "poi", default: "" },
			{ name: "end_POI", label: "End POI (optional)", type: "poi", default: "" },
			{ name: "easing", label: "Easing (s)", type: "range", default: 0, min: 0, max: 2, step: 0.1 },
			{ name: "dimmer_easing", label: "Dimmer Easing", type: "range", default: 0, min: 0, max: 1, step: 0.05 },
			{ name: "max_dim", label: "Max Dimmer", type: "range", default: 1, min: 0, max: 1, step: 0.1 },
		],
		fixtureTypes: ["moving_head"],
	},
	set_channels: {
		name: "set_channels",
		label: "Set Channels",
		params: [],
	},
};

export function getEffectSchema(effectName: string, fixtureType?: string): EffectSchema | undefined {
	const entry = EFFECT_SCHEMAS[effectName.toLowerCase()];
	if (!entry) return undefined;
	if (!Array.isArray(entry)) return entry;
	if (fixtureType) {
		const exact = entry.find((schema) => schema.fixtureTypes?.includes(fixtureType));
		if (exact) return exact;
	}
	return entry[0];
}

export function getDefaultParams(effectName: string, fixtureType?: string): Record<string, unknown> {
	const schema = getEffectSchema(effectName, fixtureType);
	if (!schema) return {};
	const defaults: Record<string, unknown> = {};
	for (const param of schema.params) {
		if (param.default !== undefined) {
			defaults[param.name] = param.default;
		}
	}
	return defaults;
}

export function getDefaultDurationSeconds(effectName: string, bpm: number, fixtureType?: string): number {
	const schema = getEffectSchema(effectName, fixtureType);
	const beats = schema?.defaultDurationBeats;
	if (beats !== undefined && Number.isFinite(bpm) && bpm > 0) {
		return (beats * 60) / bpm;
	}
	return 1;
}
