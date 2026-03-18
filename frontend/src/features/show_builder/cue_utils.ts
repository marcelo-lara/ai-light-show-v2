import type {
	ChaserCueEntry,
	ChaserDefinition,
	CueEntry,
	EffectCueEntry,
} from "../../shared/transport/protocol.ts";

export function isChaserCue(cue: CueEntry): cue is ChaserCueEntry {
	return typeof (cue as Partial<ChaserCueEntry>).chaser_id === "string";
}

export function isEffectCue(cue: CueEntry): cue is EffectCueEntry {
	return typeof (cue as Partial<EffectCueEntry>).fixture_id === "string"
		&& typeof (cue as Partial<EffectCueEntry>).effect === "string";
}

export function formatCueLabel(value: string): string {
	return value.replace(/[_-]+/g, " ").trim();
}

export function getChaserById(chasers: ChaserDefinition[], chaserId: string): ChaserDefinition | undefined {
	return chasers.find((chaser) => chaser.id === chaserId);
}

export function getCueRepetitions(cue: CueEntry): number {
	const repetitions = Number(cue.data?.repetitions ?? 1);
	if (!Number.isFinite(repetitions)) return 1;
	return Math.max(1, Math.floor(repetitions));
}

export function getChaserCycleBeats(chaser: ChaserDefinition): number {
	return chaser.effects.reduce((max, effect) => Math.max(max, effect.beat + effect.duration), 0);
}

export function getCueDurationSeconds(cue: CueEntry, chasers: ChaserDefinition[], bpm: number): number {
	if (isEffectCue(cue)) return cue.duration;
	const chaser = getChaserById(chasers, cue.chaser_id);
	if (!chaser || !Number.isFinite(bpm) || bpm <= 0) return 0;
	return (getChaserCycleBeats(chaser) * getCueRepetitions(cue) * 60) / bpm;
}

export function getCueSignatureToken(cue: CueEntry): string {
	if (isEffectCue(cue)) {
		return [cue.time, cue.fixture_id, cue.effect, cue.duration, JSON.stringify(cue.data ?? {})].join("|");
	}
	return [cue.time, cue.chaser_id, getCueRepetitions(cue), JSON.stringify(cue.data ?? {})].join("|");
}
