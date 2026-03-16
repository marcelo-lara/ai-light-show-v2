# pyright: reportAttributeAccessIssue=false

from __future__ import annotations

import time
from typing import Any, Dict, List

from models.chasers import get_chaser_by_name, load_chasers
from models.cues import upsert_cue_entries
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

    def _current_bpm(self) -> float:
        try:
            return float(getattr(self.current_song.meta, "bpm", 0.0) or 0.0)
        except (AttributeError, TypeError, ValueError):
            return 0.0

    def _expand_chaser_entries(
        self,
        chaser,
        start_time_ms: float,
        repetitions: int,
        bpm: float,
    ) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        cycle_beats = max((float(effect.beat) for effect in chaser.effects), default=0.0) + 1.0

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

    async def apply_chaser(self, chaser_name: str, start_time_ms: float, repetitions: int) -> Dict[str, Any]:
        async with self.lock:
            if not self.cue_sheet:
                return {"ok": False, "reason": "no_cue_sheet"}

            if not self.chasers:
                self.load_chasers()
            chaser = get_chaser_by_name(self.chasers, chaser_name)
            if not chaser:
                return {"ok": False, "reason": "unknown_chaser", "chaser_name": chaser_name}

            bpm = self._current_bpm()
            if bpm <= 0.0:
                return {"ok": False, "reason": "bpm_unavailable"}

            reps = max(1, int(repetitions))
            entries = self._expand_chaser_entries(chaser, max(0.0, float(start_time_ms)), reps, bpm)
            for entry in entries:
                entry["created_by"] = f"chaser:{chaser.name}"

            counts = upsert_cue_entries(self.cue_sheet, entries)
            await self.save_cue_sheet()
            self._refresh_canvas_after_cue_change()
            return {"ok": True, "chaser_name": chaser.name, "entries": len(entries), **counts}

    async def start_chaser_instance(self, chaser_name: str, start_time_ms: float, repetitions: int) -> Dict[str, Any]:
        result = await self.apply_chaser(chaser_name, start_time_ms, repetitions)
        if not result.get("ok"):
            return result

        instance_id = f"chaser-{int(time.time() * 1000)}"
        async with self.lock:
            self.active_chasers[instance_id] = {
                "chaser_name": result.get("chaser_name"),
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
