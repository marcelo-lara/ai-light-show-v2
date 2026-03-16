from __future__ import annotations

from typing import Any, Dict, List

from models.song.beats import Beat


def _beats_to_seconds(beat_count: float, bpm: float) -> float:
    return float(beat_count) * (60.0 / float(bpm))


def generate_downbeats_and_beats(beats: List[Beat], bpm: float) -> List[Dict[str, Any]]:
    """Generate cue entries for DownBeats and Beats pattern.

    - Flash mini_beam_prism_l and mini_beam_prism_r on first_beat (beat==1) for 0.5 beats
    - Then chase blue on parcan_pl, parcan_pr, parcan_l, parcan_r for 1.5 beats
      on subsequent beats in left-to-right order
    """
    entries: List[Dict[str, Any]] = []

    beats_by_bar: Dict[int, List[Beat]] = {}
    for beat in beats:
        if beat.bar not in beats_by_bar:
            beats_by_bar[beat.bar] = []
        beats_by_bar[beat.bar].append(beat)

    for bar_beats in beats_by_bar.values():
        bar_beats.sort(key=lambda b: b.beat)

    for _bar, bar_beats in beats_by_bar.items():
        if not bar_beats:
            continue

        first_beat = next((b for b in bar_beats if b.beat == 1), None)
        if first_beat:
            entries.append({
                "time": first_beat.time,
                "fixture_id": "mini_beam_prism_l",
                "effect": "flash",
                "duration": _beats_to_seconds(2, bpm),
                "data": {},
            })
            entries.append({
                "time": first_beat.time,
                "fixture_id": "mini_beam_prism_r",
                "effect": "flash",
                "duration": _beats_to_seconds(2, bpm),
                "data": {},
            })

        parcan_fixtures = ["parcan_pl", "parcan_pr", "parcan_l", "parcan_r"]
        subsequent_beats = [b for b in bar_beats if b.beat > 1]
        subsequent_beats.sort(key=lambda b: b.beat)

        for i, beat in enumerate(subsequent_beats):
            fixture_id = parcan_fixtures[i % len(parcan_fixtures)]
            entries.append({
                "time": beat.time,
                "fixture_id": fixture_id,
                "effect": "flash",
                "duration": _beats_to_seconds(1.25, bpm),
            })

    return entries
