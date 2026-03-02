from __future__ import annotations

from typing import Any, Dict, List, Optional
import json

from fastapi import WebSocket, WebSocketDisconnect

from services.artnet import ArtNetService
from services.song_service import SongService
from store.state import StateManager


class WebSocketManager:
    def __init__(self, state_manager: StateManager, artnet_service: ArtNetService, song_service: SongService):
        self.state_manager = state_manager
        self.artnet_service = artnet_service
        self.song_service = song_service
        self.active_connections: List[WebSocket] = []
        self.seq: int = 0
        self.fixture_armed: Dict[str, bool] = {}

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
        msg = {
            "type": "snapshot",
            "seq": self._next_seq(),
            "state": state,
        }
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

        before = await self._build_frontend_state()
        changed = await self._apply_intent(name, payload)

        if changed:
            after = await self._build_frontend_state()
            await self._broadcast_patch(before, after)

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
            for channel_name, value in values.items():
                if channel_name not in fixture.channels:
                    continue
                try:
                    v = int(value)
                except Exception:
                    continue
                channel = int(fixture.channels[channel_name])
                applied = await self.state_manager.update_dmx_channel(channel, max(0, min(255, v)))
                should_flush = should_flush or applied

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
            channels = {}
            for channel_name, channel_num in (fixture.channels or {}).items():
                try:
                    idx = int(channel_num) - 1
                    if 0 <= idx < len(universe):
                        channels[channel_name] = int(universe[idx])
                except Exception:
                    continue

            ftype = str(fixture.type or "").lower()
            capabilities: Dict[str, Any] = {}
            if "moving" in ftype and "head" in ftype:
                capabilities["pan_tilt"] = True
            if "rgb" in ftype or {"red", "green", "blue"}.issubset(set((fixture.channels or {}).keys())):
                capabilities["rgb"] = True

            fixtures[fixture.id] = {
                "id": fixture.id,
                "name": fixture.name,
                "type": fixture.type,
                "armed": bool(self.fixture_armed.get(fixture.id, True)),
                "values": dict(fixture.current_values or {}),
                "channels": channels,
                "capabilities": capabilities,
            }

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
        }

    async def _broadcast_patch(self, before: Dict[str, Any], after: Dict[str, Any]):
        changes = []
        keys = sorted(set(before.keys()) | set(after.keys()))
        for key in keys:
            if before.get(key) != after.get(key):
                changes.append({"path": [key], "value": after.get(key)})

        if not changes:
            return

        await self.broadcast({
            "type": "patch",
            "seq": self._next_seq(),
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
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
