# pyright: reportAttributeAccessIssue=false

from typing import Any, Dict, List, Optional

from models.cues import (
    CueEntry,
    create_cue_entry,
    delete_cue_entry,
    read_cue_entries,
    save_cue_sheet,
    update_cue_entry,
)


class StateSongCueMixin:
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

            if self.is_playing:
                self.canvas_dirty = True
            else:
                self.canvas_dirty = False
                self.canvas = self._render_cue_sheet_to_canvas()
                song_name = self.cue_sheet.song_filename
                print(
                    f"[DMX CANVAS] re-render complete for '{song_name}' — "
                    f"frames={self.canvas.total_frames} fps={self.canvas.fps}",
                    flush=True,
                )
                self._dump_canvas_debug(song_name)

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
            await self.save_cue_sheet()

            if self.is_playing:
                self.canvas_dirty = True
            else:
                self.canvas_dirty = False
                self.canvas = self._render_cue_sheet_to_canvas()
                song_name = self.cue_sheet.song_filename
                print(
                    f"[DMX CANVAS] re-render complete for '{song_name}' — "
                    f"frames={self.canvas.total_frames} fps={self.canvas.fps}",
                    flush=True,
                )
                self._dump_canvas_debug(song_name)

            return {
                "ok": True,
                "entry": entry.model_dump(),
            }

    async def save_cue_sheet(self):
        if self.cue_sheet:
            save_cue_sheet(self.backend_path / "cues", self.cue_sheet)

    def get_cue_entries(self) -> List[Dict[str, Any]]:
        """Return cue entries as list of dicts for frontend state."""
        if not self.cue_sheet:
            return []
        return read_cue_entries(self.cue_sheet)

    async def update_cue_entry(self, index: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        async with self.lock:
            if not self.cue_sheet:
                return {"ok": False, "reason": "no_cue_sheet"}
            try:
                entry = update_cue_entry(self.cue_sheet, index, payload)
            except IndexError as exc:
                return {"ok": False, "reason": str(exc)}
            await self.save_cue_sheet()
            return {"ok": True, "entry": entry.model_dump()}

    async def delete_cue_entry(self, index: int) -> Dict[str, Any]:
        async with self.lock:
            if not self.cue_sheet:
                return {"ok": False, "reason": "no_cue_sheet"}
            try:
                entry = delete_cue_entry(self.cue_sheet, index)
            except IndexError as exc:
                return {"ok": False, "reason": str(exc)}
            await self.save_cue_sheet()
            return {"ok": True, "entry": entry.model_dump()}
