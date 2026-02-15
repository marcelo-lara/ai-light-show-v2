import asyncio
import contextlib
import math
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import json
from urllib.parse import quote
from uuid import uuid4
from models.fixture import Fixture, Parcan, MovingHead
from models.cue import CueSheet, CueEntry
from models.song import Song, SongMetadata
from store.dmx_canvas import DMXCanvas, DMX_CHANNELS

FPS = 60
MAX_SONG_SECONDS = 6 * 60

class StateManager:
    def __init__(self, backend_path: Path, songs_path: Path = None, cues_path: Path = None, metadata_path: Path = None):
        self.backend_path = backend_path
        self.songs_path = songs_path or backend_path / "songs"
        self.cues_path = cues_path or backend_path / "cues"
        self.metadata_path = metadata_path or backend_path / "metadata"
        self.lock = asyncio.Lock()
        # "editor" universe reflects UI slider edits (always updated by deltas).
        self.editor_universe: bytearray = bytearray(DMX_CHANNELS)
        # "output" universe is what we actually send to Art-Net.
        self.output_universe: bytearray = bytearray(DMX_CHANNELS)
        self.fixtures: List[Fixture] = []
        self.pois: List[Dict[str, Any]] = []
        self.fixtures_path: Optional[Path] = None
        self.current_song: Optional[Song] = None
        self.cue_sheet: Optional[CueSheet] = None
        self.timecode: float = 0.0
        self.is_playing: bool = False
        self.canvas: Optional[DMXCanvas] = None
        self.song_length_seconds: float = 0.0
        self.canvas_dirty: bool = False
        self.current_frame_index: int = 0
        self.preview_active: bool = False
        self.preview_task: Optional[asyncio.Task] = None
        self.preview_canvas: Optional[DMXCanvas] = None
        self.preview_request_id: Optional[str] = None
        self.preview_fixture_id: Optional[str] = None
        self.preview_effect: Optional[str] = None
        self.preview_duration: float = 0.0
        # Highest 1-based DMX channel referenced by any fixture channel map.
        # Used to limit payload sizes when sending full-frame snapshots to the frontend.
        self.max_used_channel: int = 0

    def _get_fixture(self, fixture_id: str) -> Optional[Fixture]:
        return next((fixture for fixture in self.fixtures if fixture.id == fixture_id), None)

    def _fixture_supported_effects(self, fixture: Fixture) -> set[str]:
        runtime_effects = {
            "moving_head": {"set_channels", "move_to", "seek", "strobe", "full", "flash", "sweep"},
            "parcan": {"set_channels", "flash", "strobe", "fade_in", "full"},
            "rgb": {"set_channels", "flash", "strobe", "fade_in", "full"},
        }.get((fixture.type or "").lower(), {"set_channels"})

        declared = {
            str(effect).strip().lower()
            for effect in (fixture.effects or [])
            if str(effect).strip()
        }
        if not declared:
            return runtime_effects
        return runtime_effects.intersection(declared)

    async def get_status(self) -> Dict[str, Any]:
        async with self.lock:
            preview = None
            if self.preview_active:
                preview = {
                    "requestId": self.preview_request_id,
                    "fixtureId": self.preview_fixture_id,
                    "effect": self.preview_effect,
                    "duration": float(self.preview_duration),
                }
            return {
                "isPlaying": bool(self.is_playing),
                "previewActive": bool(self.preview_active),
                "preview": preview,
            }

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
            self.fixtures_path = Path(fixtures_path)
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

    async def load_pois(self, pois_path: Path):
        async with self.lock:
            with open(pois_path, 'r') as f:
                data = json.load(f)

            if isinstance(data, list):
                self.pois = [item for item in data if isinstance(item, dict)]
            else:
                self.pois = []

    async def get_pois(self) -> List[Dict[str, Any]]:
        async with self.lock:
            return [dict(poi) for poi in self.pois]

    async def save_fixtures(self) -> None:
        if not self.fixtures_path:
            raise RuntimeError("fixtures_path_not_set")

        fixtures_payload = [fixture.dict() for fixture in self.fixtures]
        self.fixtures_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.fixtures_path, 'w') as f:
            json.dump(fixtures_payload, f, indent=2)

    async def update_fixture_poi_target(self, fixture_id: str, poi_id: str, pan: int, tilt: int) -> Dict[str, Any]:
        async with self.lock:
            fixture = self._get_fixture(str(fixture_id or "").strip())
            if not fixture:
                return {"ok": False, "reason": "fixture_not_found"}

            if (fixture.type or "").lower() not in {"moving_head", "moving-head"}:
                return {"ok": False, "reason": "fixture_not_moving_head"}

            normalized_poi_id = str(poi_id or "").strip()
            if not normalized_poi_id:
                return {"ok": False, "reason": "invalid_poi_id"}

            poi_exists = any(
                str((poi or {}).get("id") or "").strip() == normalized_poi_id
                for poi in self.pois
            )
            if not poi_exists:
                return {"ok": False, "reason": "poi_not_found"}

            pan_u16 = max(0, min(65535, int(pan)))
            tilt_u16 = max(0, min(65535, int(tilt)))

            poi_targets = fixture.poi_targets if isinstance(fixture.poi_targets, dict) else {}
            poi_targets[normalized_poi_id] = {
                "pan": pan_u16,
                "tilt": tilt_u16,
            }
            fixture.poi_targets = poi_targets

            await self.save_fixtures()

            return {
                "ok": True,
                "fixture_id": fixture.id,
                "poi_id": normalized_poi_id,
                "values": {
                    "pan": pan_u16,
                    "tilt": tilt_u16,
                },
            }

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
            audio_url = None
            audio_file = self.songs_path / f"{song_filename}.mp3"
            if audio_file.exists():
                audio_url = f"/songs/{quote(audio_file.name)}"
            # Load metadata
            metadata_file = self.metadata_path / f"{song_filename}.metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata_data = json.load(f)
                    metadata = SongMetadata(**metadata_data)
            else:
                metadata = SongMetadata(filename=song_filename, parts={}, hints={}, drums={})

            self.current_song = Song(filename=song_filename, metadata=metadata, audioUrl=audio_url)

            self.song_length_seconds = self._infer_song_length_seconds(metadata)

            # Load cue sheet
            cue_file = self.cues_path / f"{song_filename}.cue.json"
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
            self.preview_active = False
            self.preview_task = None
            self.preview_canvas = None
            self.preview_request_id = None
            self.preview_fixture_id = None
            self.preview_effect = None
            self.preview_duration = 0.0
            self.canvas_dirty = False
            self.canvas = self._render_cue_sheet_to_canvas()
            # Debug: indicate canvas render completion for visibility in Docker logs
            try:
                print(f"[DMX CANVAS] render complete for '{song_filename}' — frames={self.canvas.total_frames} fps={self.canvas.fps}", flush=True)
            except Exception:
                print("[DMX CANVAS] render complete", flush=True)
            # Dump debug file with per-frame timecodes and used DMX channels
            try:
                self._dump_canvas_debug(song_filename)
            except Exception:
                pass

    async def update_dmx_channel(self, channel: int, value: int) -> bool:
        """Update the editor universe with a live edit.

        Returns whether this edit should be applied to output immediately.
        During playback edits are disabled.
        """
        async with self.lock:
            if self.is_playing:
                return False
            if 1 <= channel <= DMX_CHANNELS and 0 <= value <= 255:
                self.editor_universe[channel - 1] = value
                if not self.is_playing and not self.preview_active:
                    self.output_universe[channel - 1] = value
                    return True
            return False

    async def start_preview_effect(
        self,
        fixture_id: str,
        effect: str,
        duration: float,
        data: Optional[Dict[str, Any]],
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        cancel_task: Optional[asyncio.Task] = None

        async with self.lock:
            if self.is_playing:
                return {"ok": False, "reason": "playback_active"}

            fixture = self._get_fixture(str(fixture_id or "").strip())
            if not fixture:
                return {"ok": False, "reason": "fixture_not_found"}

            normalized_effect = str(effect or "").strip().lower()
            if normalized_effect not in self._fixture_supported_effects(fixture):
                return {"ok": False, "reason": "effect_not_supported"}

            preview_duration = float(duration or 0.0)
            if preview_duration <= 0:
                return {"ok": False, "reason": "invalid_duration"}

            rid = str(request_id or uuid4())

            if self.preview_task:
                cancel_task = self.preview_task

            base_universe = bytearray(self.editor_universe)
            self.preview_canvas = self._render_preview_canvas(
                fixture=fixture,
                effect=normalized_effect,
                duration=preview_duration,
                data=data or {},
                base_universe=base_universe,
            )
            self.preview_request_id = rid
            self.preview_fixture_id = fixture.id
            self.preview_effect = normalized_effect
            self.preview_duration = preview_duration
            self.preview_active = True
            self.output_universe[:] = self.preview_canvas.frame_view(0)

            self.preview_task = asyncio.create_task(self._run_preview(rid))

        if cancel_task:
            cancel_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await cancel_task

        return {
            "ok": True,
            "requestId": rid,
            "fixtureId": fixture_id,
            "effect": normalized_effect,
            "duration": float(preview_duration),
        }

    async def cancel_preview(self) -> bool:
        task: Optional[asyncio.Task] = None
        async with self.lock:
            if not self.preview_active and not self.preview_task:
                return False

            task = self.preview_task
            self.preview_active = False
            self.preview_task = None
            self.preview_canvas = None
            self.preview_request_id = None
            self.preview_fixture_id = None
            self.preview_effect = None
            self.preview_duration = 0.0

            if self.is_playing:
                self.current_frame_index = self._time_to_frame_index(self.timecode)
                self._apply_canvas_frame_to_output(self.current_frame_index)
            else:
                self.output_universe[:] = self.editor_universe

        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        return True

    async def wait_for_preview_end(self, request_id: str) -> None:
        task: Optional[asyncio.Task] = None
        async with self.lock:
            if self.preview_request_id != request_id:
                return
            task = self.preview_task
        if task:
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def get_output_universe(self) -> bytearray:
        async with self.lock:
            return bytearray(self.output_universe)

    async def get_editor_universe(self) -> bytearray:
        async with self.lock:
            return bytearray(self.editor_universe)

    async def add_cue_entry(self, timecode: float, name: Optional[str] = None) -> List[CueEntry]:
        """Record effects into the cue sheet.

        Current UI is "plain control" (sliders) so this records a set_channels effect per fixture
        capturing the editor universe at the given time.

        While playing, effects are recorded but NOT rendered in real-time (canvas becomes dirty).
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
                # Debug: indicate canvas render completion when cues are added while paused
                try:
                    song_name = self.cue_sheet.song_filename if self.cue_sheet else song_filename
                    print(f"[DMX CANVAS] re-render complete for '{song_name}' — frames={self.canvas.total_frames} fps={self.canvas.fps}", flush=True)
                except Exception:
                    print("[DMX CANVAS] re-render complete", flush=True)
                # Dump debug file after re-render
                try:
                    self._dump_canvas_debug(song_name)
                except Exception:
                    pass

            return new_entries

    async def save_cue_sheet(self):
        if self.cue_sheet:
            cues_path = self.backend_path / "cues"
            cues_path.mkdir(parents=True, exist_ok=True)
            cue_file = cues_path / f"{self.cue_sheet.song_filename}.cue.json"
            with open(cue_file, 'w') as f:
                json.dump(self.cue_sheet.dict(), f, indent=2)

    async def set_playback_state(self, is_playing: bool) -> None:
        task_to_cancel: Optional[asyncio.Task] = None
        async with self.lock:
            self.is_playing = bool(is_playing)
            if self.is_playing:
                if self.preview_task:
                    task_to_cancel = self.preview_task
                self.preview_active = False
                self.preview_task = None
                self.preview_canvas = None
                self.preview_request_id = None
                self.preview_fixture_id = None
                self.preview_effect = None
                self.preview_duration = 0.0
                self.current_frame_index = self._time_to_frame_index(self.timecode)
                self._apply_canvas_frame_to_output(self.current_frame_index)
            elif not self.preview_active:
                self.output_universe[:] = self.editor_universe

        if task_to_cancel:
            task_to_cancel.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task_to_cancel

    async def seek_timecode(self, timecode: float) -> None:
        """Hard jump to a timecode (frame skipping allowed)."""
        async with self.lock:
            self.timecode = float(timecode or 0.0)
            self.current_frame_index = self._time_to_frame_index(self.timecode)
            if self.preview_active and not self.is_playing:
                return
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
        cues.sort(key=lambda x: (x[0], x[2].fixture_id, x[2].effect))
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
                active_sorted = sorted(active, key=lambda x: (x[2].time, x[2].fixture_id, x[2].effect))
                for start_frame, end_frame, entry in active_sorted:
                    self._render_entry_into_universe(universe, frame_index, start_frame, end_frame, entry, entry_render_state)

            canvas.set_frame(frame_index, universe)

        return canvas

    def _render_preview_canvas(
        self,
        *,
        fixture: Fixture,
        effect: str,
        duration: float,
        data: Dict[str, Any],
        base_universe: bytearray,
    ) -> DMXCanvas:
        total_frames = max(1, int(math.ceil(float(duration) * FPS)) + 1)
        canvas = DMXCanvas.allocate(fps=FPS, total_frames=total_frames)
        universe = bytearray(base_universe)
        render_state: Dict[str, Any] = {}

        end_frame = total_frames - 1
        for frame_index in range(total_frames):
            fixture.render_effect(
                universe,
                effect=effect,
                frame_index=frame_index,
                start_frame=0,
                end_frame=end_frame,
                fps=FPS,
                data=data,
                render_state=render_state,
            )
            canvas.set_frame(frame_index, universe)

        return canvas

    async def _run_preview(self, request_id: str) -> None:
        try:
            async with self.lock:
                if not self.preview_canvas or self.preview_request_id != request_id:
                    return
                total_frames = self.preview_canvas.total_frames

            for frame_index in range(total_frames):
                async with self.lock:
                    if self.preview_request_id != request_id or not self.preview_canvas:
                        return
                    if self.is_playing:
                        return
                    self.output_universe[:] = self.preview_canvas.frame_view(frame_index)

                if frame_index + 1 < total_frames:
                    await asyncio.sleep(1.0 / FPS)
        except asyncio.CancelledError:
            raise
        finally:
            async with self.lock:
                if self.preview_request_id != request_id:
                    return

                final_frame: Optional[bytearray] = None
                if self.preview_canvas and self.preview_canvas.total_frames > 0:
                    final_frame = bytearray(self.preview_canvas.frame_view(self.preview_canvas.total_frames - 1))

                self.preview_active = False
                self.preview_task = None
                self.preview_canvas = None
                self.preview_request_id = None
                self.preview_fixture_id = None
                self.preview_effect = None
                self.preview_duration = 0.0

                if self.is_playing:
                    self.current_frame_index = self._time_to_frame_index(self.timecode)
                    self._apply_canvas_frame_to_output(self.current_frame_index)
                else:
                    if final_frame is not None:
                        self.editor_universe[:] = final_frame
                        self.output_universe[:] = final_frame
                    else:
                        self.output_universe[:] = self.editor_universe

    def _dump_canvas_debug(self, song_filename: str) -> None:
        """Write a LOG debug file of non-empty frames to backend/cues.

        Each line is formatted like the backend logs:
        [<time_seconds>] AA.BB.CC.00.00... (hex pairs, uppercase, dot-separated)

        To keep files compact we only write frames that have any non-zero channel
        value within the highest referenced channel (self.max_used_channel).
        """
        try:
            if not self.canvas:
                return
            cues_path = self.backend_path / "cues"
            cues_path.mkdir(parents=True, exist_ok=True)
            debug_file = cues_path / f"{song_filename}.canvas.debug.log"
            frames_written = 0
            # Limit written channels to the highest referenced channel to keep lines smaller.
            max_ch = self.max_used_channel or DMX_CHANNELS
            max_ch = max(1, min(DMX_CHANNELS, int(max_ch)))
            with open(debug_file, 'w') as f:
                for frame_index in range(self.canvas.total_frames):
                    view = self.canvas.frame_view(frame_index)
                    # Check for any non-zero within the used channel range.
                    if not any(b != 0 for b in view[:max_ch]):
                        continue
                    # Format time with millisecond precision like logs.
                    time_sec = frame_index / float(self.canvas.fps)
                    hex_pairs = ".".join(f"{int(b):02X}" for b in view[:max_ch])
                    f.write(f"[{time_sec:.3f}] {hex_pairs}\n")
                    frames_written += 1
            print(f"[DMX CANVAS] dumped debug file '{debug_file}' — frames={frames_written}", flush=True)
        except Exception as exc:
            print(f"[DMX CANVAS] failed to write debug file: {exc}", flush=True)

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

        # Delegate effect rendering to the fixture type.
        state_key = id(entry)
        render_state = entry_render_state.setdefault(state_key, {})
        fixture.render_effect(
            universe,
            effect=entry.effect,
            frame_index=frame_index,
            start_frame=start_frame,
            end_frame=end_frame,
            fps=FPS,
            data=entry.data or {},
            render_state=render_state,
        )