# pyright: reportAttributeAccessIssue=false

from urllib.parse import quote

from models.cues import load_cue_sheet
from models.song import Song
from store.dmx_canvas import DMX_CHANNELS


class StateSongLoadingMixin:
    async def load_song(self, song_filename: str):
        async with self.lock:
            audio_url = None
            audio_file = self.songs_path / f"{song_filename}.mp3"
            if audio_file.exists():
                audio_url = f"/songs/{quote(audio_file.name)}"

            # Let the Song class handle lazy loading internally!
            self.current_song = Song(
                song_id=song_filename, 
                base_dir=str(self.meta_path),
                audio_url=audio_url
            )
            self.song_length_seconds = self._infer_song_length_seconds(self.current_song)

            self.load_chasers()
            self.cue_sheet = load_cue_sheet(self.cues_path, song_filename)
            self.load_human_hints(song_filename)
            self._validate_cue_sheet()

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
            self.active_chasers = {}
            self.canvas_dirty = False
            self.canvas = self._render_cue_sheet_to_canvas()
            print(
                f"[DMX CANVAS] render complete for '{song_filename}' — "
                f"frames={self.canvas.total_frames} fps={self.canvas.fps}",
                flush=True,
            )
            self._dump_canvas_debug(song_filename)
