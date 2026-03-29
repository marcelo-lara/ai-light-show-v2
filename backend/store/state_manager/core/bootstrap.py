import asyncio
from time import perf_counter
from pathlib import Path
from typing import Any, Dict, List, Optional

from models.fixtures.fixture import Fixture
from store.dmx_canvas import DMX_CHANNELS, DMXCanvas
from store.pois import PoiStore

class StateCoreBootstrapMixin:
    def __init__(
        self,
        backend_path: Path,
        songs_path: Optional[Path] = None,
        cues_path: Optional[Path] = None,
        meta_path: Optional[Path] = None,
    ):
        self.backend_path = backend_path
        self.songs_path = songs_path or backend_path / "songs"
        self.cues_path = cues_path or backend_path / "cues"
        self.meta_path = meta_path or backend_path / "meta"
        self.lock = asyncio.Lock()
        self.editor_universe: bytearray = bytearray(DMX_CHANNELS)
        self.output_universe: bytearray = bytearray(DMX_CHANNELS)
        self.fixtures: List[Fixture] = []
        self.poi_db: PoiStore = PoiStore(backend_path / "fixtures" / "pois.json")
        self.fixtures_path: Optional[Path] = None
        self.current_song = None
        self.cue_sheet = None
        self.timecode: float = 0.0
        self.is_playing: bool = False
        self.playback_anchor_perf: float = perf_counter()
        self.playback_anchor_timecode: float = 0.0
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
        self.preview_chaser_active: bool = False
        self.preview_chaser_task: Optional[asyncio.Task] = None
        self.preview_chaser_canvas: Optional[DMXCanvas] = None
        self.preview_chaser_request_id: Optional[str] = None
        self.preview_chaser_name: Optional[str] = None
        self.max_used_channel: int = 0
        self.chasers_path: Path = backend_path / "fixtures" / "chasers.json"
        self.chasers: List[Any] = []
        self.active_chasers: Dict[str, Dict[str, Any]] = {}

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

    async def get_is_playing(self) -> bool:
        async with self.lock:
            return bool(self.is_playing)

    async def get_timecode(self) -> float:
        async with self.lock:
            if self.is_playing:
                return float(self._current_playback_timecode_locked(perf_counter()))
            return float(self.timecode)

    async def get_max_used_channel(self) -> int:
        async with self.lock:
            return int(self.max_used_channel)

    async def get_output_universe(self) -> bytearray:
        async with self.lock:
            return bytearray(self.output_universe)

    async def get_editor_universe(self) -> bytearray:
        async with self.lock:
            return bytearray(self.editor_universe)
