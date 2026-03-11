# pyright: reportAttributeAccessIssue=false

import json
from typing import Dict, List, Optional

from models.cue import CueEntry


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
                    CueEntry(
                        time=float(timecode),
                        fixture_id=fixture.id,
                        effect="set_channels",
                        duration=0.0,
                        data={"channels": channel_values},
                        name=name,
                    )
                )

            self.cue_sheet.entries.extend(new_entries)
            self.cue_sheet.entries.sort(key=lambda e: (e.time, e.fixture_id, e.effect))
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

    async def save_cue_sheet(self):
        if self.cue_sheet:
            cues_path = self.backend_path / "cues"
            cues_path.mkdir(parents=True, exist_ok=True)
            cue_file = cues_path / f"{self.cue_sheet.song_filename}.cue.json"
            with open(cue_file, "w") as f:
                json.dump(self.cue_sheet.dict(), f, indent=2)
