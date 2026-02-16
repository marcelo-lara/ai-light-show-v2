from fastapi import WebSocket, WebSocketDisconnect
from typing import List
import json
from store.state import StateManager
from services.artnet import ArtNetService
from services.song_service import SongService

class WebSocketManager:
    def __init__(self, state_manager: StateManager, artnet_service: ArtNetService, song_service: SongService):
        self.state_manager = state_manager
        self.artnet_service = artnet_service
        self.song_service = song_service
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Send initial state
        await self.send_initial_state(websocket)
        # If we're not playing, also send a full-frame snapshot so the frontend's
        # fixtures lane reflects current values (including arm defaults).
        if not await self.state_manager.get_is_playing():
            await self.send_dmx_frame_snapshot(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_initial_state(self, websocket: WebSocket):
        fixtures = [f.dict() for f in self.state_manager.fixtures]
        cues = self.state_manager.cue_sheet.dict() if self.state_manager.cue_sheet else None
        song = self.state_manager.current_song.dict() if self.state_manager.current_song else None
        initial_state = {
            "type": "initial",
            "fixtures": fixtures,
            "cues": cues,
            "song": song,
            "playback": {
                "fps": 60,
                "songLengthSeconds": getattr(self.state_manager, "song_length_seconds", 0.0),
                "isPlaying": getattr(self.state_manager, "is_playing", False),
            },
        }
        await websocket.send_json(initial_state)

    async def send_dmx_frame_snapshot(self, websocket: WebSocket) -> None:
        """Send the current output universe as a compact snapshot.

        Payload is limited to the highest channel referenced by any fixture.
        The frontend treats this as authoritative for the fixtures lane while paused.
        """
        max_used = await self.state_manager.get_max_used_channel()
        universe = await self.state_manager.get_output_universe()
        timecode = await self.state_manager.get_timecode()
        values = list(universe[:max(0, min(len(universe), int(max_used)))])
        await websocket.send_json({
            "type": "dmx_frame",
            "time": float(timecode),
            "values": values,
        })

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

    async def handle_message(self, websocket: WebSocket, data: str):
        try:
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == "delta":
                channel = message.get("channel")
                value = message.get("value")
                should_apply = await self.state_manager.update_dmx_channel(channel, value)
                if should_apply:
                    universe = await self.state_manager.get_output_universe()
                    await self.artnet_service.update_universe(universe)
                # Broadcast delta
                await self.broadcast({"type": "delta", "channel": channel, "value": value})

            elif msg_type == "timecode":
                timecode = message.get("time")
                # While paused, the backend must NOT be driven by timecode updates.
                if await self.state_manager.get_is_playing():
                    await self.state_manager.update_timecode(timecode)
                    universe = await self.state_manager.get_output_universe()
                    await self.artnet_service.update_universe(universe)

            elif msg_type == "seek":
                timecode = message.get("time")
                await self.state_manager.seek_timecode(timecode)
                universe = await self.state_manager.get_output_universe()
                await self.artnet_service.update_universe(universe)
                # While paused, seeking should also update the frontend fixtures lane
                # by sending the closest canvas frame (no streaming during playback).
                if not await self.state_manager.get_is_playing():
                    await self.send_dmx_frame_snapshot(websocket)

            elif msg_type == "playback":
                playing = bool(message.get("playing", False))
                await self.state_manager.set_playback_state(playing)

            elif msg_type == "add_cue":
                timecode = message.get("time")
                name = message.get("name")
                await self.state_manager.add_cue_entry(timecode, name)
                # Broadcast updated cue sheet (add_cue now appends multiple effect entries).
                if self.state_manager.cue_sheet:
                    await self.broadcast({"type": "cues_updated", "cues": self.state_manager.cue_sheet.dict()})

            elif msg_type == "load_song":
                song_filename = message.get("filename")
                await self.state_manager.load_song(song_filename)
                universe = await self.state_manager.get_output_universe()
                await self.artnet_service.update_universe(universe)
                # Broadcast new state
                for conn in self.active_connections:
                    await self.send_initial_state(conn)
                    if not await self.state_manager.get_is_playing():
                        await self.send_dmx_frame_snapshot(conn)

            elif msg_type == "chat":
                prompt = message.get("message")
                # Mock echo
                response = f"Echo: {prompt}"
                await websocket.send_json({"type": "chat_response", "message": response})

        except Exception as e:
            print(f"Error handling message: {e}")

async def websocket_endpoint(websocket: WebSocket, manager: WebSocketManager):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

    # end
