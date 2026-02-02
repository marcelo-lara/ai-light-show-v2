import asyncio
import math
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import json
from urllib.parse import quote
from models.fixture import Fixture, Parcan, MovingHead
from models.cue import CueSheet, CueEntry
from models.song import Song, SongMetadata
from store.dmx_canvas import DMXCanvas, DMX_CHANNELS

FPS = 60
MAX_SONG_SECONDS = 6 * 60

class StateManager:
    def __init__(self, backend_path: Path):
        self.backend_path = backend_path
        self.lock = asyncio.Lock()
        # "editor" universe reflects UI slider edits (always updated by deltas).
        self.editor_universe: bytearray = bytearray(DMX_CHANNELS)
        # "output" universe is what we actually send to Art-Net.
        self.output_universe: bytearray = bytearray(DMX_CHANNELS)
        self.fixtures: List[Fixture] = []
        self.current_song: Optional[Song] = None
        self.cue_sheet: Optional[CueSheet] = None
        self.timecode: float = 0.0
        self.is_playing: bool = False
        self.canvas: Optional[DMXCanvas] = None
        self.song_length_seconds: float = 0.0
        self.canvas_dirty: bool = False
        self.current_frame_index: int = 0
        # Highest 1-based DMX channel referenced by any fixture channel map.
        # Used to limit payload sizes when sending full-frame snapshots to the frontend.
        self.max_used_channel: int = 0

    def _infer_song_length_seconds(self, metadata: SongMetadata) -> float:
        # Prefer explicit metadata if it ever gets added later.
        raw = getattr(metadata, "duration", None)
        if isinstance(raw, (int, float)) and raw > 0:
            return float(raw)

        # Fall back to derived max timestamp from parts/hints/drums.
        max_t = 0.0
        try:
            for _name, rng in (metadata.parts or {}).items():
                if isinstance(rng, list) and len(rng) >= 2:
                    max_t = max(max_t, float(rng[1]))
        except Exception:
            pass

        try:
            for _name, times in (metadata.hints or {}).items():
                for t in times or []:
                    max_t = max(max_t, float(t))
        except Exception:
            pass

        try:
            for _name, times in (metadata.drums or {}).items():
                for t in times or []:
                    max_t = max(max_t, float(t))
        except Exception:
            pass

        if max_t <= 0:
            max_t = float(MAX_SONG_SECONDS)
        return min(float(MAX_SONG_SECONDS), max_t)

    def _set_channel(self, universe: bytearray, channel_1_based: int, value: int) -> None:
        if 1 <= channel_1_based <= DMX_CHANNELS:
            universe[channel_1_based - 1] = max(0, min(255, int(value)))

    def _apply_arm(self, universe: bytearray) -> None:
        for fixture in self.fixtures:
            for channel_name, value in (fixture.arm or {}).items():
                if channel_name in fixture.channels:
                    self._set_channel(universe, fixture.channels[channel_name], value)

    async def load_fixtures(self, fixtures_path: Path):
        async with self.lock:
            with open(fixtures_path, 'r') as f:
                data = json.load(f)
                fixtures: List[Fixture] = []
                for fixture in data:
                    ftype = fixture.get('type', '').lower()
                    try:
                        if ftype == 'moving_head' or ftype == 'moving-head':
                            obj = MovingHead(**fixture)
                        else:
                            # default to parcan for unknown/empty types
                            obj = Parcan(**fixture)
                    except Exception:
                        # Fallback: try base Fixture (non-abstract) if parsing differs
                        obj = Parcan(**fixture)
                    fixtures.append(obj)
                self.fixtures = fixtures

            # Compute highest referenced 1-based channel for smaller frontend snapshots.
            max_ch = 0
            for fixture in self.fixtures:
                for ch in (fixture.channels or {}).values():
                    try:
                        max_ch = max(max_ch, int(ch))
                    except Exception:
                        pass
            self.max_used_channel = max(0, min(DMX_CHANNELS, int(max_ch)))

            # Apply arm defaults to both editor and output universes.
            self.editor_universe = bytearray(DMX_CHANNELS)
            self.output_universe = bytearray(DMX_CHANNELS)
            self._apply_arm(self.editor_universe)
            self._apply_arm(self.output_universe)

    async def get_is_playing(self) -> bool:
        async with self.lock:
            return bool(self.is_playing)

    async def get_timecode(self) -> float:
        async with self.lock:
            return float(self.timecode)

    async def get_max_used_channel(self) -> int:
        async with self.lock:
            return int(self.max_used_channel)

    async def load_song(self, song_filename: str):
        async with self.lock:
            songs_path = self.backend_path / "songs"
            cues_path = self.backend_path / "cues"
            metadata_path = self.backend_path / "metadata"
            audio_url = None
            audio_file = songs_path / f"{song_filename}.mp3"
            if audio_file.exists():
                audio_url = f"/songs/{quote(audio_file.name)}"
            # Load metadata
            metadata_file = metadata_path / f"{song_filename}.metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata_data = json.load(f)
                    metadata = SongMetadata(**metadata_data)
            else:
                metadata = SongMetadata(filename=song_filename, parts={}, hints={}, drums={})

            self.current_song = Song(filename=song_filename, metadata=metadata, audioUrl=audio_url)

            self.song_length_seconds = self._infer_song_length_seconds(metadata)

            # Load cue sheet
            cue_file = cues_path / f"{song_filename}.cue.json"
            if cue_file.exists():
                with open(cue_file, 'r') as f:
                    cue_data = json.load(f)
                    self.cue_sheet = CueSheet(**cue_data)
            else:
                self.cue_sheet = CueSheet(song_filename=song_filename, entries=[])

            # Reset universes and build canvas for the whole song.
            self.editor_universe = bytearray(DMX_CHANNELS)
            self.output_universe = bytearray(DMX_CHANNELS)
            self._apply_arm(self.editor_universe)
            self._apply_arm(self.output_universe)
            self.is_playing = False
            self.timecode = 0.0
            self.current_frame_index = 0
            self.canvas_dirty = False
            self.canvas = self._render_cue_sheet_to_canvas()

    async def update_dmx_channel(self, channel: int, value: int) -> bool:
        """Update the editor universe with a live edit.

        Returns whether this edit should be applied to output immediately.
        During playback we ignore live edits for output (but still track them for authoring).
        """
        async with self.lock:
            if 1 <= channel <= DMX_CHANNELS and 0 <= value <= 255:
                self.editor_universe[channel - 1] = value
                if not self.is_playing:
                    self.output_universe[channel - 1] = value
                    return True
            return False

    async def get_output_universe(self) -> bytearray:
        async with self.lock:
            return bytearray(self.output_universe)

    async def get_editor_universe(self) -> bytearray:
        async with self.lock:
            return bytearray(self.editor_universe)

    async def add_cue_entry(self, timecode: float, name: Optional[str] = None) -> List[CueEntry]:
        """Record actions into the cue sheet.

        Current UI is "plain control" (sliders) so this records a set_channels action per fixture
        capturing the editor universe at the given time.

        While playing, actions are recorded but NOT rendered in real-time (canvas becomes dirty).
        """
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
                        action="set_channels",
                        duration=0.0,
                        data={"channels": channel_values},
                        name=name,
                    )
                )

            self.cue_sheet.entries.extend(new_entries)
            self.cue_sheet.entries.sort(key=lambda e: (e.time, e.fixture_id, e.action))
            await self.save_cue_sheet()

            if self.is_playing:
                self.canvas_dirty = True
            else:
                self.canvas_dirty = False
                self.canvas = self._render_cue_sheet_to_canvas()

            return new_entries

    async def save_cue_sheet(self):
        if self.cue_sheet:
            cues_path = self.backend_path / "cues"
            cues_path.mkdir(parents=True, exist_ok=True)
            cue_file = cues_path / f"{self.cue_sheet.song_filename}.cue.json"
            with open(cue_file, 'w') as f:
                json.dump(self.cue_sheet.dict(), f, indent=2)

    async def set_playback_state(self, is_playing: bool) -> None:
        async with self.lock:
            self.is_playing = bool(is_playing)

    async def seek_timecode(self, timecode: float) -> None:
        """Hard jump to a timecode (frame skipping allowed)."""
        async with self.lock:
            self.timecode = float(timecode or 0.0)
            self.current_frame_index = self._time_to_frame_index(self.timecode)
            self._apply_canvas_frame_to_output(self.current_frame_index)

    async def update_timecode(self, timecode: float) -> None:
        """Update playback time.

        Audio is authoritative; backend selects the closest DMX canvas frame.
        We intentionally do NOT simulate intermediate frames if time jumps.
        """
        async with self.lock:
            self.timecode = float(timecode or 0.0)
            self.current_frame_index = self._time_to_frame_index(self.timecode)
            self._apply_canvas_frame_to_output(self.current_frame_index)

    def _time_to_frame_index(self, timecode: float) -> int:
        if not self.canvas:
            return 0
        frame = int(round(float(timecode) * float(self.canvas.fps)))
        return self.canvas.clamp_frame_index(frame)

    def _apply_canvas_frame_to_output(self, frame_index: int) -> None:
        if not self.canvas:
            return
        self.output_universe[:] = self.canvas.frame_view(frame_index)

    def _iter_cues_for_render(self) -> List[Tuple[int, int, CueEntry]]:
        """Prepare cues sorted with computed frame ranges."""
        if not self.cue_sheet:
            return []
        cues: List[Tuple[int, int, CueEntry]] = []
        for entry in self.cue_sheet.entries:
            start = int(round(float(entry.time) * FPS))
            dur = max(0.0, float(entry.duration or 0.0))
            end = int(round((float(entry.time) + dur) * FPS))
            cues.append((start, end, entry))
        cues.sort(key=lambda x: (x[0], x[2].fixture_id, x[2].action))
        return cues

    def _render_cue_sheet_to_canvas(self) -> DMXCanvas:
        total_frames = max(1, int(math.ceil(self.song_length_seconds * FPS)) + 1)
        canvas = DMXCanvas.allocate(fps=FPS, total_frames=total_frames)

        base_universe = bytearray(DMX_CHANNELS)
        self._apply_arm(base_universe)

        # Group cues by start frame for efficient incremental activation.
        cues = self._iter_cues_for_render()
        cues_by_start: Dict[int, List[Tuple[int, int, CueEntry]]] = {}
        for start, end, entry in cues:
            cues_by_start.setdefault(start, []).append((start, end, entry))

        active: List[Tuple[int, int, CueEntry]] = []
        universe = bytearray(base_universe)

        # Per-entry render state cache (e.g. move_to start positions).
        entry_render_state: Dict[int, Dict[str, Any]] = {}

        for frame_index in range(total_frames):
            # Activate any cues starting at this frame.
            if frame_index in cues_by_start:
                active.extend(cues_by_start[frame_index])

            # Drop finished cues.
            if active:
                active = [(start, end, entry) for (start, end, entry) in active if end >= frame_index]

            # Apply active cue effects for this frame.
            if active:
                # Stable order for deterministic overlaps.
                active_sorted = sorted(active, key=lambda x: (x[2].time, x[2].fixture_id, x[2].action))
                for start_frame, end_frame, entry in active_sorted:
                    self._render_entry_into_universe(universe, frame_index, start_frame, end_frame, entry, entry_render_state)

            canvas.set_frame(frame_index, universe)

        return canvas

    def _render_entry_into_universe(
        self,
        universe: bytearray,
        frame_index: int,
        start_frame: int,
        end_frame: int,
        entry: CueEntry,
        entry_render_state: Dict[int, Dict[str, Any]],
    ) -> None:
        fixture = next((f for f in self.fixtures if f.id == entry.fixture_id), None)
        if not fixture:
            return

        # Delegate action rendering to the fixture type.
        state_key = id(entry)
        render_state = entry_render_state.setdefault(state_key, {})
        fixture.render_action(
            universe,
            action=entry.action,
            frame_index=frame_index,
            start_frame=start_frame,
            end_frame=end_frame,
            fps=FPS,
            data=entry.data or {},
            render_state=render_state,
        )