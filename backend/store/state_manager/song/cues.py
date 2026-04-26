# pyright: reportAttributeAccessIssue=false

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from models.cues import (
    CueEntry,
    clear_cue_sheet,
    create_cue_entry,
    delete_cue_entry,
    load_cue_sheet,
    read_cue_entries,
    save_cue_sheet,
    update_cue_entry,
    upsert_cue_entries,
)


class StateSongCueMixin:
    def get_chasers(self) -> List[Dict[str, Any]]:
        """Return merged list of global and local chasers (local wins)."""
        global_chasers = getattr(self, "chasers", [])
        local_chasers = []
        if self.cue_sheet and hasattr(self.cue_sheet, "chasers") and self.cue_sheet.chasers:
            local_chasers = self.cue_sheet.chasers

        # Convert to dicts if they are models
        g_dicts = [c if isinstance(c, dict) else c.model_dump() for c in global_chasers]
        l_dicts = [c if isinstance(c, dict) else c.model_dump() for c in local_chasers]

        merged = {c["id"]: c for c in g_dicts}
        merged.update({c["id"]: c for c in l_dicts})

        return list(merged.values())

    def get_chaser_definition(self, chaser_id: str) -> Optional[Dict[str, Any]]:
        """Resolve chaser by ID: local song scope first, then global library."""
        # 1. Local
        if self.cue_sheet and hasattr(self.cue_sheet, "chasers") and self.cue_sheet.chasers:
            for c in self.cue_sheet.chasers:
                cid = c.get("id") if isinstance(c, dict) else getattr(c, "id", None)
                if cid == chaser_id:
                    return c if isinstance(c, dict) else c.model_dump()

        # 2. Global
        global_chasers = getattr(self, "chasers", [])
        for c in global_chasers:
            cid = c.get("id") if isinstance(c, dict) else getattr(c, "id", None)
            if cid == chaser_id:
                return c if isinstance(c, dict) else c.model_dump()

        return None

    @staticmethod
    def _cue_sort_key(entry: CueEntry) -> tuple[float, str, str]:
        label = entry.chaser_id or entry.fixture_id or ""
        effect = entry.effect or ""
        return (entry.time, label, effect)

    def _validate_cue_entry(self, entry: CueEntry) -> None:
        if entry.is_chaser:
            chaser = self.get_chaser_definition(entry.chaser_id or "")
            if not chaser:
                raise ValueError("unknown_chaser_id")
            return

        fixture = self._get_fixture(entry.fixture_id or "")
        if not fixture:
            raise ValueError("fixture_not_found")

        supported = self._fixture_supported_effects(fixture)
        effect_lower = str(entry.effect or "").lower().strip()
        if effect_lower not in supported:
            raise ValueError("effect_not_supported")

    def _validate_cue_sheet(self) -> None:
        if not self.cue_sheet:
            return
        for entry in self.cue_sheet.entries:
            self._validate_cue_entry(entry)

    def _refresh_canvas_after_cue_change(self) -> None:
        self.canvas_dirty = False
        self.canvas = self._render_cue_sheet_to_canvas()
        song_name = self.cue_sheet.song_filename
        print(
            f"[DMX CANVAS] re-render complete for '{song_name}' — "
            f"frames={self.canvas.total_frames} fps={self.canvas.fps}",
            flush=True,
        )
        self._dump_canvas_debug(song_name)

        if self.is_playing:
            self.current_frame_index = self._time_to_frame_index(self.timecode)
            self._apply_canvas_frame_to_output(self.current_frame_index)

    async def reload_cue_sheet_from_disk(self) -> Dict[str, Any]:
        async with self.lock:
            song_filename = getattr(self.cue_sheet, "song_filename", None) or getattr(self.current_song, "song_id", None)
            if not song_filename:
                return {"ok": False, "reason": "no_song_loaded"}

            current_cue_sheet = self.cue_sheet
            next_cue_sheet = load_cue_sheet(self.cues_path, song_filename)
            try:
                self.cue_sheet = next_cue_sheet
                self._validate_cue_sheet()
            except ValueError as exc:
                self.cue_sheet = current_cue_sheet
                return {"ok": False, "reason": str(exc), "song_filename": song_filename}

            self._refresh_canvas_after_cue_change()
            return {
                "ok": True,
                "song_filename": song_filename,
                "count": len(self.cue_sheet.entries),
                "entries": self.get_cue_entries(),
            }

    async def add_cue_entry(self, timecode: float, name: Optional[str] = None) -> List[CueEntry]:
        async with self.lock:
            if not self.cue_sheet:
                return []

            new_entries: List[CueEntry] = []
            for fixture in self.fixtures:
                channel_values: Dict[str, int] = {}
                for channel_name, channel_num in fixture.channels.items():
                    channel_values[channel_name] = int(self.editor_universe[channel_num - 1])

                new_entries.append(
                    create_cue_entry(
                        self.cue_sheet,
                        {
                            "time": float(timecode),
                            "fixture_id": fixture.id,
                            "effect": "set_channels",
                            "duration": 0.0,
                            "data": {"channels": channel_values},
                            "name": name,
                        },
                    )
                )

            await self.save_cue_sheet()
            self._refresh_canvas_after_cue_change()

            return new_entries

    async def add_effect_cue_entry(
        self,
        time: float,
        fixture_id: str,
        effect: str,
        duration: float,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Add a single effect cue entry for a specific fixture.

        Returns dict with "ok": True/False and additional info.
        """
        async with self.lock:
            if not self.cue_sheet:
                return {"ok": False, "reason": "no_cue_sheet"}

            fixture = self._get_fixture(fixture_id)
            if not fixture:
                return {"ok": False, "reason": "fixture_not_found", "fixture_id": fixture_id}

            supported = self._fixture_supported_effects(fixture)
            effect_lower = effect.lower().strip()
            if effect_lower not in supported:
                return {
                    "ok": False,
                    "reason": "effect_not_supported",
                    "fixture_id": fixture_id,
                    "effect": effect,
                    "supported": list(supported),
                }

            entry = create_cue_entry(
                self.cue_sheet,
                {
                    "time": float(time),
                    "fixture_id": fixture_id,
                    "effect": effect_lower,
                    "duration": float(duration),
                    "data": data,
                },
            )
            self._validate_cue_entry(entry)
            await self.save_cue_sheet()
            self._refresh_canvas_after_cue_change()

            return {
                "ok": True,
                "entry": entry.model_dump(exclude_none=True),
            }

    async def add_chaser_cue_entry(
        self,
        time: float,
        chaser_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        async with self.lock:
            if not self.cue_sheet:
                return {"ok": False, "reason": "no_cue_sheet"}

            current_entries = list(self.cue_sheet.entries)
            entry = create_cue_entry(
                self.cue_sheet,
                {
                    "time": float(time),
                    "chaser_id": chaser_id,
                    "data": data if isinstance(data, dict) else {},
                },
            )
            try:
                self._validate_cue_entry(entry)
            except ValueError as exc:
                self.cue_sheet.entries = current_entries
                return {"ok": False, "reason": str(exc)}
            await self.save_cue_sheet()
            self._refresh_canvas_after_cue_change()
            return {"ok": True, "entry": entry.model_dump(exclude_none=True)}

    async def save_cue_sheet(self):
        if self.cue_sheet:
            save_cue_sheet(self.backend_path / "cues", self.cue_sheet)

    def get_cue_entries(self) -> List[Dict[str, Any]]:
        """Return cue entries as list of dicts for frontend state."""
        if not self.cue_sheet:
            return []
        return read_cue_entries(self.cue_sheet)

    def get_cue_entries_window(self, start_time: float, end_time: float) -> List[Dict[str, Any]]:
        if end_time < start_time:
            raise ValueError("invalid_time_range")
        entries = self.get_cue_entries()
        return [entry for entry in entries if start_time <= float(entry.get("time", 0.0)) <= end_time]

    async def replace_cue_entries_window(
        self,
        start_time: float,
        end_time: float,
        entries: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        async with self.lock:
            if not self.cue_sheet:
                return {"ok": False, "reason": "no_cue_sheet"}
            if end_time < start_time:
                return {"ok": False, "reason": "invalid_time_range"}

            current_entries = list(self.cue_sheet.entries)
            try:
                replacement_entries = [CueEntry(**entry) for entry in entries]
            except Exception as exc:
                return {"ok": False, "reason": "invalid_entry", "error": str(exc)}

            for entry in replacement_entries:
                if not (float(start_time) <= float(entry.time) <= float(end_time)):
                    return {
                        "ok": False,
                        "reason": "entry_out_of_window",
                        "entry": entry.model_dump(exclude_none=True),
                    }

            retained_entries = [
                entry for entry in current_entries if not (float(start_time) <= float(entry.time) <= float(end_time))
            ]
            self.cue_sheet.entries = self._dedupe_entries(retained_entries + replacement_entries)
            try:
                self._validate_cue_sheet()
            except ValueError as exc:
                self.cue_sheet.entries = current_entries
                return {"ok": False, "reason": str(exc)}

            await self.save_cue_sheet()
            self._refresh_canvas_after_cue_change()
            return {
                "ok": True,
                "start_time": float(start_time),
                "end_time": float(end_time),
                "count": len(self.cue_sheet.entries),
                "window_count": len(replacement_entries),
                "entries": self.get_cue_entries(),
            }

    async def replace_cue_sheet_entries(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        async with self.lock:
            if not self.cue_sheet:
                return {"ok": False, "reason": "no_cue_sheet"}

            current_entries = list(self.cue_sheet.entries)
            try:
                next_entries = [CueEntry(**entry) for entry in entries]
            except Exception as exc:
                return {"ok": False, "reason": "invalid_entry", "error": str(exc)}

            self.cue_sheet.entries = next_entries
            self.cue_sheet.entries = self._dedupe_entries(self.cue_sheet.entries)
            try:
                self._validate_cue_sheet()
            except ValueError as exc:
                self.cue_sheet.entries = current_entries
                return {"ok": False, "reason": str(exc)}

            await self.save_cue_sheet()
            self._refresh_canvas_after_cue_change()
            return {
                "ok": True,
                "count": len(self.cue_sheet.entries),
                "entries": self.get_cue_entries(),
            }

    def _dedupe_entries(self, entries: List[CueEntry]) -> List[CueEntry]:
        from models.cues.crud import _dedupe_entries

        return _dedupe_entries(entries)

    async def update_cue_entry(self, index: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with self.lock:
            if not self.cue_sheet:
                return {"ok": False, "reason": "no_cue_sheet"}
            current_entries = list(self.cue_sheet.entries)
            try:
                entry = update_cue_entry(self.cue_sheet, index, payload)
            except IndexError as exc:
                return {"ok": False, "reason": str(exc)}
            except ValueError as exc:
                return {"ok": False, "reason": str(exc)}
            try:
                self._validate_cue_entry(entry)
            except ValueError as exc:
                self.cue_sheet.entries = current_entries
                return {"ok": False, "reason": str(exc)}
            await self.save_cue_sheet()
            self._refresh_canvas_after_cue_change()
            return {"ok": True, "entry": entry.model_dump(exclude_none=True)}

    async def delete_cue_entry(self, index: int) -> Dict[str, Any]:
        async with self.lock:
            if not self.cue_sheet:
                return {"ok": False, "reason": "no_cue_sheet"}
            try:
                entry = delete_cue_entry(self.cue_sheet, index)
            except IndexError as exc:
                return {"ok": False, "reason": str(exc)}
            await self.save_cue_sheet()
            self._refresh_canvas_after_cue_change()
            return {"ok": True, "entry": entry.model_dump(exclude_none=True)}

    async def clear_cue_entries(
        self,
        from_time: float = 0.0,
        to_time: Optional[float] = None,
    ) -> Dict[str, Any]:
        async with self.lock:
            if not self.cue_sheet:
                return {"ok": False, "reason": "no_cue_sheet"}
            if to_time is not None and to_time < from_time:
                return {"ok": False, "reason": "invalid_time_range"}

            cues_path = self.backend_path / "cues"
            song_filename = self.cue_sheet.song_filename
            before_count = len(self.cue_sheet.entries)

            clear_cue_sheet(cues_path, song_filename, from_time=from_time, to_time=to_time)
            self.cue_sheet = load_cue_sheet(cues_path, song_filename)

            removed = before_count - len(self.cue_sheet.entries)
            if removed > 0:
                self._refresh_canvas_after_cue_change()

            return {
                "ok": True,
                "removed": max(0, removed),
                "remaining": len(self.cue_sheet.entries),
            }

    async def clear_all_cue_entries(self) -> Dict[str, Any]:
        return await self.clear_cue_entries(from_time=0.0, to_time=None)

    async def upsert_chaser_definition(
        self,
        chaser_id: str,
        name: str,
        description: str,
        effects: List[Dict[str, Any]],
        is_global: bool = False
    ) -> Dict[str, Any]:
        """Creates or updates a chaser definition in the specified scope."""
        new_def = {
            "id": chaser_id,
            "name": name,
            "description": description,
            "effects": effects
        }

        async with self.lock:
            if is_global:
                # Update global fixtures/chasers.json
                global_path = self.backend_path / "fixtures" / "chasers.json"
                try:
                    data = []
                    if global_path.exists():
                        with open(global_path, "r") as f:
                            data = json.load(f)
                    
                    # Update or append
                    idx = -1
                    for i, c in enumerate(data):
                        if c.get("id") == chaser_id:
                            idx = i
                            break
                    
                    if idx >= 0:
                        data[idx] = new_def
                    else:
                        data.append(new_def)
                    
                    with open(global_path, "w") as f:
                        json.dump(data, f, indent=2)
                    
                    # Update runtime cache
                    if hasattr(self, "chasers"):
                        setattr(self, "chasers", data)
                except Exception as e:
                    return {"ok": False, "reason": f"global_save_failed: {str(e)}"}
            else:
                if not self.cue_sheet:
                    return {"ok": False, "reason": "no_song_loaded"}
                
                # Update local cue_sheet.chasers
                if not hasattr(self.cue_sheet, "chasers") or self.cue_sheet.chasers is None:
                    self.cue_sheet.chasers = []
                
                # Check for existing
                idx = -1
                for i, c in enumerate(self.cue_sheet.chasers):
                    cid = c.get("id") if isinstance(c, dict) else getattr(c, "id", None)
                    if cid == chaser_id:
                        idx = i
                        break
                
                if idx >= 0:
                    self.cue_sheet.chasers[idx] = new_def
                else:
                    self.cue_sheet.chasers.append(new_def)
                
                await self.save_cue_sheet()
                self._refresh_canvas_after_cue_change()
            
            return {"ok": True, "chaser": new_def}

    async def apply_cue_helper(self, helper_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Apply a cue helper to generate and upsert cue entries."""
        from services.cue_helpers import generate_cue_helper_entries, get_cue_helper_definition

        async with self.lock:
            if not self.cue_sheet:
                return {"ok": False, "reason": "no_cue_sheet"}

            if not self.current_song:
                return {"ok": False, "reason": "no_song_loaded"}

            helper = get_cue_helper_definition(helper_id)
            if not helper:
                return {"ok": False, "reason": "unknown_helper_id", "helper_id": helper_id}

            if helper.get("requires_beats") and (not self.current_song.beats or not self.current_song.beats.beats):
                return {"ok": False, "reason": "beats_unavailable"}

            try:
                bpm = float(getattr(self.current_song.meta, "bpm", 0.0) or 0.0)
            except (TypeError, ValueError):
                bpm = 0.0
            if bpm <= 0.0:
                return {"ok": False, "reason": "bpm_unavailable"}

            beats = self.current_song.beats.beats if self.current_song.beats and self.current_song.beats.beats else []
            try:
                new_entries = generate_cue_helper_entries(
                    helper_id,
                    beats=beats,
                    bpm=bpm,
                    params=params,
                    song=self.current_song,
                    fixtures=list(self.fixtures),
                    pois=list(self.pois),
                    supported_effects=self._fixture_supported_effects,
                )
            except ValueError as exc:
                result = {"ok": False, "reason": str(exc), "helper_id": helper_id}
                missing_artifacts = getattr(exc, "missing_artifacts", None)
                if missing_artifacts:
                    result["missing_artifacts"] = missing_artifacts
                return result

            try:
                for entry in new_entries:
                    self._validate_cue_entry(CueEntry(**entry))
            except Exception as exc:
                return {"ok": False, "reason": str(exc), "helper_id": helper_id}

            for entry in new_entries:
                entry["created_by"] = helper_id

            # Apply upsert logic
            counts = upsert_cue_entries(self.cue_sheet, new_entries)
            await self.save_cue_sheet()
            self._refresh_canvas_after_cue_change()

            return {"ok": True, **counts}
