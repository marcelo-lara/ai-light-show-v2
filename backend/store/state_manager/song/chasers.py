# pyright: reportAttributeAccessIssue=false

from __future__ import annotations

import time
from typing import Any, Dict, List

from models.chasers import get_chaser_by_id, get_chaser_cycle_beats, load_chasers
from models.cues import create_cue_entry
from services.cue_helpers.timing import beatToTimeMs


class StateSongChaserMixin:
    def load_chasers(self) -> None:
        try:
            self.chasers = load_chasers(self.chasers_path)
        except Exception as exc:
            self.chasers = []
            print(f"[CHASERS] failed to load {self.chasers_path}: {exc}", flush=True)

    def get_chasers(self) -> List[Dict[str, Any]]:
        if not self.chasers:
            self.load_chasers()
        return [item.model_dump() for item in self.chasers]

    def get_chaser_definition(self, chaser_id: str):
        if not self.chasers:
            self.load_chasers()
        return get_chaser_by_id(self.chasers, chaser_id)

    def _current_bpm(self) -> float:
        try:
            return float(getattr(self.current_song.meta, "bpm", 0.0) or 0.0)
        except (AttributeError, TypeError, ValueError):
            return 0.0

    def get_chaser_repetitions(self, cue_data: Dict[str, Any] | None) -> int:
        try:
            repetitions = int((cue_data or {}).get("repetitions", 1))
        except (TypeError, ValueError):
            repetitions = 1
        return max(1, repetitions)

    def get_chaser_duration_seconds(self, chaser_id: str, repetitions: int, bpm: float) -> float:
        if bpm <= 0.0:
            return 0.0
        chaser = self.get_chaser_definition(chaser_id)
        if not chaser:
            return 0.0
        total_beats = get_chaser_cycle_beats(chaser) * max(1, repetitions)
        return beatToTimeMs(total_beats, bpm) / 1000.0

    def expand_chaser_entries(
        self,
        chaser_id: str,
        start_time_ms: float,
        repetitions: int,
        bpm: float,
    ) -> List[Dict[str, Any]]:
        chaser = self.get_chaser_definition(chaser_id)
        if not chaser:
            return []
        entries: List[Dict[str, Any]] = []
        cycle_beats = get_chaser_cycle_beats(chaser)

        for cycle in range(repetitions):
            cycle_offset_beats = cycle * cycle_beats
            for effect in chaser.effects:
                cue_time_ms = start_time_ms + beatToTimeMs(cycle_offset_beats + effect.beat, bpm)
                cue_duration_ms = beatToTimeMs(effect.duration, bpm)
                entries.append({
                    "time": cue_time_ms / 1000.0,
                    "fixture_id": effect.fixture_id,
                    "effect": effect.effect,
                    "duration": cue_duration_ms / 1000.0,
                    "data": dict(effect.data),
                })
        return entries

    async def apply_chaser(self, chaser_id: str, start_time_ms: float, repetitions: int) -> Dict[str, Any]:
        async with self.lock:
            if not self.cue_sheet:
                return {"ok": False, "reason": "no_cue_sheet"}

            chaser = self.get_chaser_definition(chaser_id)
            if not chaser:
                return {"ok": False, "reason": "unknown_chaser", "chaser_id": chaser_id}

            reps = max(1, int(repetitions))
            entry = create_cue_entry(
                self.cue_sheet,
                {
                    "time": max(0.0, float(start_time_ms)) / 1000.0,
                    "chaser_id": chaser.id,
                    "data": {"repetitions": reps},
                    "created_by": f"chaser:{chaser.id}",
                },
            )

            self._validate_cue_entry(entry)
            await self.save_cue_sheet()
            self._refresh_canvas_after_cue_change()
            return {"ok": True, "chaser_id": chaser.id, "entry": entry.model_dump(exclude_none=True)}

    async def start_chaser_instance(self, chaser_id: str, start_time_ms: float, repetitions: int) -> Dict[str, Any]:
        result = await self.apply_chaser(chaser_id, start_time_ms, repetitions)
        if not result.get("ok"):
            return result

        instance_id = f"chaser-{int(time.time() * 1000)}"
        async with self.lock:
            self.active_chasers[instance_id] = {
                "chaser_id": result.get("chaser_id"),
                "start_time_ms": max(0.0, float(start_time_ms)),
                "repetitions": max(1, int(repetitions)),
            }
        result["instance_id"] = instance_id
        return result

    async def stop_chaser_instance(self, instance_id: str) -> Dict[str, Any]:
        async with self.lock:
            removed = self.active_chasers.pop(instance_id, None)
            if not removed:
                return {"ok": False, "reason": "unknown_instance_id", "instance_id": instance_id}
            return {"ok": True, "instance_id": instance_id}
