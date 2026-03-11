# pyright: reportAttributeAccessIssue=false

import json
from urllib.parse import quote

from models.cue import CueSheet
from models.song import Song
from store.dmx_canvas import DMX_CHANNELS


class StateSongLoadingMixin:
    async def load_song(self, song_filename: str):
        async with self.lock:
            audio_url = None
            audio_file = self.songs_path / f"{song_filename}.mp3"
            if audio_file.exists():
                audio_url = f"/songs/{quote(audio_file.name)}"

            metadata = self._load_song_metadata(song_filename)
            self.current_song = Song(filename=song_filename, metadata=metadata, audioUrl=audio_url)
            self.song_length_seconds = self._infer_song_length_seconds(metadata)

            cue_file = self.cues_path / f"{song_filename}.cue.json"
            if cue_file.exists():
                with open(cue_file, "r") as f:
                    cue_data = json.load(f)
                    self.cue_sheet = CueSheet(**cue_data)
            else:
                self.cue_sheet = CueSheet(song_filename=song_filename, entries=[])

            self.editor_universe = bytearray(DMX_CHANNELS)
            self.output_universe = bytearray(DMX_CHANNELS)
            self._apply_arm(self.editor_universe)
            self._apply_arm(self.output_universe)
            self.is_playing = False
            self.timecode = 0.0
            self.current_frame_index = 0
            self.preview_active = False
            self.preview_task = None
            self.preview_canvas = None
            self.preview_request_id = None
            self.preview_fixture_id = None
            self.preview_effect = None
            self.preview_duration = 0.0
            self.canvas_dirty = False
            self.canvas = self._render_cue_sheet_to_canvas()
            print(
                f"[DMX CANVAS] render complete for '{song_filename}' — "
                f"frames={self.canvas.total_frames} fps={self.canvas.fps}",
                flush=True,
            )
            self._dump_canvas_debug(song_filename)
