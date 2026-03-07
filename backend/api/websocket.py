from __future__ import annotations

from typing import Any, Dict, List, Optional
import json
import asyncio
import time
import logging

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self, state_manager: StateManager, artnet_service: ArtNetService, song_service: SongService):
        self.state_manager = state_manager
        self.artnet_service = artnet_service
        self.song_service = song_service
        self.active_connections: List[WebSocket] = []
        self.seq: int = 0
        self.fixture_armed: Dict[str, bool] = {}
        
        # Throttling state
        self._last_broadcast_time = 0.0
        self._broadcast_throttle_ms = 50  # ~20 FPS for state updates
        self._pending_broadcast_task: Optional[asyncio.Task] = None
        self._last_state_snapshot: Optional[Dict[str, Any]] = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self._ensure_arm_state_initialized()
        await self.send_snapshot(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_snapshot(self, websocket: WebSocket):
        state = await self._build_frontend_state()
        self._last_state_snapshot = state # track last state for future patching
        msg = {
            "type": "snapshot",
            "seq": self._next_seq(),
            "state": state,
        }
        logger.info(f"[WS] Sending snapshot to client (seq={msg['seq']}) with {len(state.get('fixtures', {}))} fixtures")
        # Log fixtures state specifically as requested
        for fid, fstate in state.get("fixtures", {}).items():
            logger.debug(f"[WS] Fixture {fid}: values={fstate.get('values')}")
        await websocket.send_json(msg)

    async def broadcast(self, message: dict):
        stale: List[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection)

    async def broadcast_event(self, level: str, message: str, data: Optional[Dict[str, Any]] = None):
        payload: Dict[str, Any] = {
            "type": "event",
            "level": level,
            "message": message,
        }
        if data is not None:
            payload["data"] = data
        await self.broadcast(payload)

    async def handle_message(self, websocket: WebSocket, data: str):
        try:
            message = json.loads(data)
        except Exception:
            await websocket.send_json({
                "type": "event",
                "level": "error",
                "message": "invalid_json",
            })
            return

        msg_type = message.get("type")

        if msg_type == "hello":
            await self.send_snapshot(websocket)
            return

        if msg_type != "intent":
            await websocket.send_json({
                "type": "event",
                "level": "warning",
                "message": "unsupported_message_type",
                "data": {"type": msg_type},
            })
            return

        name = str(message.get("name") or "")
        payload = message.get("payload") or {}
        if not isinstance(payload, dict):
            payload = {}

        if not self._last_state_snapshot:
            self._last_state_snapshot = await self._build_frontend_state()

        changed = await self._apply_intent(name, payload)

        if changed:
            await self._schedule_broadcast()

    async def _schedule_broadcast(self):
        """Schedules a throttled broadcast of the current state."""
        now = time.time()
        time_since_last = (now - self._last_broadcast_time) * 1000.0

        if self._pending_broadcast_task and not self._pending_broadcast_task.done():
            # Already a broadcast pending, it will pick up the latest state
            return

        if time_since_last >= self._broadcast_throttle_ms:
            # Enough time has passed, broadcast immediately
            await self._execute_broadcast()
        else:
            # Schedule for later
            delay = (self._broadcast_throttle_ms - time_since_last) / 1000.0
            self._pending_broadcast_task = asyncio.create_task(self._delayed_broadcast(delay))

    async def _delayed_broadcast(self, delay: float):
        await asyncio.sleep(delay)
        await self._execute_broadcast()

    async def _execute_broadcast(self):
        if not self.active_connections:
            return

        new_state = await self._build_frontend_state()
        if self._last_state_snapshot:
            await self._broadcast_patch(self._last_state_snapshot, new_state)
        else:
            # Fallback if no last snapshot exists (should be rare after first snapshot)
            logger.warning("[WS] No previous snapshot to patch against, sending full snapshot")
            await self.broadcast({
                "type": "snapshot",
                "seq": self._next_seq(),
                "state": new_state,
            })
            
        self._last_state_snapshot = new_state
        self._last_broadcast_time = time.time()

    async def _apply_intent(self, name: str, payload: Dict[str, Any]) -> bool:
        self._ensure_arm_state_initialized()

        if name == "transport.play":
            await self.state_manager.set_playback_state(True)
            await self.artnet_service.set_continuous_send(True)
            return True

        if name == "transport.pause":
            await self.state_manager.set_playback_state(False)
            await self.artnet_service.set_continuous_send(False)
            return True

        if name == "transport.stop":
            await self.state_manager.set_playback_state(False)
            await self.state_manager.seek_timecode(0.0)
            universe = await self.state_manager.get_output_universe()
            await self.artnet_service.update_universe(universe)
            await self.artnet_service.set_continuous_send(False)
            return True

        if name == "transport.jump_to_time":
            raw = payload.get("time_ms")
            try:
                target = max(0.0, float(str(raw)) / 1000.0)
            except Exception:
                await self.broadcast_event("error", "invalid_time_ms")
                return False
            await self.state_manager.seek_timecode(target)
            universe = await self.state_manager.get_output_universe()
            await self.artnet_service.update_universe(universe)
            return True

        if name == "transport.jump_to_section":
            await self.broadcast_event("warning", "jump_to_section_not_implemented")
            return False

        if name == "fixture.set_arm":
            fixture_id = str(payload.get("fixture_id") or "")
            if not fixture_id:
                await self.broadcast_event("error", "fixture_id_required")
                return False
            self.fixture_armed[fixture_id] = bool(payload.get("armed", False))
            return True

        if name == "fixture.set_values":
            fixture_id = str(payload.get("fixture_id") or "")
            values = payload.get("values") or {}
            if not fixture_id or not isinstance(values, dict):
                await self.broadcast_event("error", "invalid_fixture_values_payload")
                return False

            fixture = next((f for f in self.state_manager.fixtures if f.id == fixture_id), None)
            if not fixture:
                await self.broadcast_event("error", "fixture_not_found", {"fixture_id": fixture_id})
                return False

            should_flush = False
            channel_types = fixture.meta.get("channel_types", {})
            
            for channel_name, value in values.items():
                ctype = channel_types.get(channel_name)
                print(f"[DEBUG] WS: setting {channel_name} to {value} for {fixture_id}, ctype={ctype}")
                
                # Check for preset/POI handling
                if channel_name == "preset":
                    preset_id = str(value)
                    # Check if it's a POI for moving heads
                    if hasattr(fixture, "_find_preset_values"):
                        preset_values = fixture._find_preset_values(preset_id)
                        if preset_values:
                            # Recurse or apply direct values from the preset/POI
                            # For simplicity we apply pan/tilt directly if present
                            for k, v in preset_values.items():
                                if k in ("pan", "tilt"):
                                    # Assuming 16-bit for these
                                    msb_key, lsb_key = f"{k}_msb", f"{k}_lsb"
                                    if msb_key in fixture.channels and lsb_key in fixture.channels:
                                        iv = int(v)
                                        msb, lsb = (iv >> 8) & 0xFF, iv & 0xFF
                                        applied_msb = await self.state_manager.update_dmx_channel(int(fixture.channels[msb_key]), msb)
                                        applied_lsb = await self.state_manager.update_dmx_channel(int(fixture.channels[lsb_key]), lsb)
                                        should_flush = should_flush or applied_msb or applied_lsb
                    continue

                # Check for position_16bit handling
                if ctype == "position_16bit":
                    msb_key = f"{channel_name}_msb"
                    lsb_key = f"{channel_name}_lsb"
                    if msb_key in fixture.channels and lsb_key in fixture.channels:
                        try:
                            v = int(value)
                            msb, lsb = (v >> 8) & 0xFF, v & 0xFF
                            
                            applied_msb = await self.state_manager.update_dmx_channel(int(fixture.channels[msb_key]), msb)
                            applied_lsb = await self.state_manager.update_dmx_channel(int(fixture.channels[lsb_key]), lsb)
                            should_flush = should_flush or applied_msb or applied_lsb
                        except Exception:
                            continue
                elif channel_name in fixture.channels:
                    # Single-byte channel
                    try:
                        v = int(value)
                        applied = await self.state_manager.update_dmx_channel(int(fixture.channels[channel_name]), max(0, min(255, v)))
                        print(f"[DEBUG] WS: update_dmx_channel({fixture.channels[channel_name]}, {v}) -> {applied}")
                        should_flush = should_flush or applied
                    except Exception as e:
                        print(f"[DEBUG] WS: exception in single-byte: {e}")
                        continue
                elif ctype in fixture.channels:
                    # Logical name 'ctype' itself if maps to a fixture channel
                    try:
                        v = int(value)
                        applied = await self.state_manager.update_dmx_channel(int(fixture.channels[ctype]), max(0, min(255, v)))
                        print(f"[DEBUG] WS: update_dmx_channel({fixture.channels[ctype]}, {v}) [BY CTYPE] -> {applied}")
                        should_flush = should_flush or applied
                    except Exception as e:
                        print(f"[DEBUG] WS: exception in ctype-byte: {e}")
                        continue
                else:
                    # Fallback for raw channel names if not in types but in channels
                    # This handles things like "dim", "red", etc. that may not be in channel_types explicitly
                    if channel_name in fixture.channels:
                        try:
                            v = int(value)
                            applied = await self.state_manager.update_dmx_channel(int(fixture.channels[channel_name]), max(0, min(255, v)))
                            should_flush = should_flush or applied
                        except Exception:
                            continue

            if should_flush:
                universe = await self.state_manager.get_output_universe()
                await self.artnet_service.update_universe(universe)

            return True

        if name == "fixture.preview_effect":
            fixture_id = str(payload.get("fixture_id") or "")
            effect = str(payload.get("effect_id") or "")
            duration_ms = payload.get("duration_ms")
            params = payload.get("params") or {}

            try:
                duration = max(0.0, float(str(duration_ms)) / 1000.0)
            except Exception:
                duration = 0.5

            result = await self.state_manager.start_preview_effect(
                fixture_id=fixture_id,
                effect=effect,
                duration=duration,
                data=params if isinstance(params, dict) else {},
                request_id=None,
            )

            if not result.get("ok"):
                await self.broadcast_event("warning", "preview_rejected", result)
                return False

            universe = await self.state_manager.get_output_universe()
            await self.artnet_service.update_universe(universe)
            await self.artnet_service.set_continuous_send(True)
            await self.broadcast_event("info", "preview_started", result)
            return True

        if name == "fixture.stop_preview":
            await self.broadcast_event("warning", "stop_preview_not_implemented")
            return False

        if name == "llm.send_prompt":
            prompt = str(payload.get("prompt") or "").strip()
            if not prompt:
                await self.broadcast_event("error", "prompt_required")
                return False

            await self.broadcast_event("info", "llm_stream", {
                "domain": "llm",
                "chunk": "Echo: ",
                "done": False,
            })
            await self.broadcast_event("info", "llm_stream", {
                "domain": "llm",
                "chunk": prompt,
                "done": True,
            })
            return False

        if name == "llm.cancel":
            await self.broadcast_event("info", "llm_cancelled", {"domain": "llm"})
            return False

        await self.broadcast_event("warning", "unknown_intent", {"name": name})
        return False

    async def _build_frontend_state(self) -> Dict[str, Any]:
        status = await self.state_manager.get_status()
        timecode = await self.state_manager.get_timecode()
        universe = await self.state_manager.get_output_universe()

        is_playing = bool(status.get("isPlaying", False))
        playback_state = "playing" if is_playing else ("stopped" if timecode <= 0.001 else "paused")
        show_state = "running" if is_playing else "idle"

        section_name = self._section_name_for_time(timecode)
        bpm = None
        if self.state_manager.current_song and self.state_manager.current_song.metadata:
            bpm = self.state_manager.current_song.metadata.bpm

        fixtures = {}
        for fixture in self.state_manager.fixtures:
            # We use meta/channel_types to determine which logical values to send.
            # If a channel is position_16bit, we combine MSB/LSB from the universe.
            # Otherwise, we use the raw 8-bit value from the universe.
            
            logical_values = {}
            channel_types = fixture.meta.get("channel_types", {})
            
            # Identify which base names are parts of 16-bit values
            processed_channels = set()
            ftype = str(fixture.type or "").lower()
            capabilities: Dict[str, Any] = {}
            if "moving" in ftype and "head" in ftype:
                capabilities["pan_tilt"] = True
            
            for channel_name, channel_type in channel_types.items():
                if channel_type == "position_16bit":
                    msb_key = f"{channel_name}_msb"
                    lsb_key = f"{channel_name}_lsb"
                    if msb_key in fixture.channels and lsb_key in fixture.channels:
                        msb_idx = int(fixture.channels[msb_key]) - 1
                        lsb_idx = int(fixture.channels[lsb_key]) - 1
                        if 0 <= msb_idx < len(universe) and 0 <= lsb_idx < len(universe):
                            val = (int(universe[msb_idx]) << 8) | int(universe[lsb_idx])
                            logical_values[channel_name] = val
                        processed_channels.add(msb_key)
                        processed_channels.add(lsb_key)
                else:
                    # Single byte channel mapped by type (dimmer, color, etc.)
                    target_channel_name = channel_type
                    if target_channel_name in fixture.channels:
                        idx = int(fixture.channels[target_channel_name]) - 1
                        if 0 <= idx < len(universe):
                            logical_values[channel_name] = int(universe[idx])
                            processed_channels.add(target_channel_name)

            if "rgb" in ftype or {"red", "green", "blue"}.issubset(set((fixture.channels or {}).keys())):
                capabilities["rgb"] = True

            fixtures[fixture.id] = {
                "id": fixture.id,
                "name": fixture.name,
                "type": fixture.type,
                "armed": bool(self.fixture_armed.get(fixture.id, True)),
                "values": logical_values,
                "capabilities": capabilities,
            }

        song_payload = self._build_song_payload()

        return {
            "system": {
                "show_state": show_state,
                "edit_lock": is_playing,
            },
            "playback": {
                "state": playback_state,
                "time_ms": int(round(timecode * 1000.0)),
                "bpm": bpm,
                "section_name": section_name,
            },
            "fixtures": fixtures,
            "song": song_payload,
            "pois": await self.state_manager.get_pois(),
        }

    def _build_song_payload(self) -> Optional[Dict[str, Any]]:
        song = self.state_manager.current_song
        if not song:
            return None

        metadata = getattr(song, "metadata", None)
        hints = getattr(metadata, "hints", {}) or {}
        drums = getattr(metadata, "drums", {}) or {}
        parts = getattr(metadata, "parts", {}) or {}

        sections: List[Dict[str, Any]] = []
        for name, rng in parts.items():
            if not isinstance(rng, list) or len(rng) < 2:
                continue
            try:
                start = float(rng[0])
                end = float(rng[1])
            except Exception:
                continue
            sections.append({
                "name": str(name),
                "start_s": start,
                "end_s": end,
            })

        sections.sort(key=lambda item: float(item.get("start_s", 0.0)))

        def _pick_numeric_list(*candidates: Any) -> List[float]:
            for candidate in candidates:
                if not isinstance(candidate, list):
                    continue
                picked: List[float] = []
                for value in candidate:
                    try:
                        picked.append(float(value))
                    except Exception:
                        continue
                if picked:
                    return picked
            return []

        beats = _pick_numeric_list(hints.get("beats"), drums.get("beats"))
        downbeats = _pick_numeric_list(hints.get("downbeats"), drums.get("downbeats"))

        return {
            "filename": str(getattr(song, "filename", "") or ""),
            "audio_url": getattr(song, "audioUrl", None),
            "length_s": getattr(metadata, "length", None),
            "bpm": getattr(metadata, "bpm", None),
            "sections": sections,
            "beats": beats,
            "downbeats": downbeats,
        }

    async def _broadcast_patch(self, before: Dict[str, Any], after: Dict[str, Any]):
        changes = []
        keys = sorted(set(before.keys()) | set(after.keys()))
        for key in keys:
            if before.get(key) != after.get(key):
                changes.append({"path": [key], "value": after.get(key)})

        if not changes:
            return

        seq = self._next_seq()
        logger.info(f"[WS] Broadcasting patch (seq={seq}) with {len(changes)} changes")
        for change in changes:
            if change["path"] == ["fixtures"]:
                logger.debug(f"[WS] Fixtures changed: {json.dumps(change['value'], indent=2)}")

        await self.broadcast({
            "type": "patch",
            "seq": seq,
            "changes": changes,
        })

    def _section_name_for_time(self, timecode: float) -> Optional[str]:
        song = self.state_manager.current_song
        if not song or not song.metadata or not song.metadata.parts:
            return None

        t = float(timecode)
        for name, rng in song.metadata.parts.items():
            if isinstance(rng, list) and len(rng) >= 2:
                try:
                    start = float(rng[0])
                    end = float(rng[1])
                except Exception:
                    continue
                if start <= t <= end:
                    return str(name)
        return None

    def _ensure_arm_state_initialized(self):
        if self.fixture_armed:
            return
        for fixture in self.state_manager.fixtures:
            self.fixture_armed[fixture.id] = True

    def _next_seq(self) -> int:
        self.seq += 1
        return self.seq

async def websocket_endpoint(websocket: WebSocket, manager: WebSocketManager):
    logger.info(f"[WS] Connect request from {websocket.client}")
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"[WS] Message received: {data[:100]}...")
            await manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        logger.info("[WS] Disconnected")
        manager.disconnect(websocket)
