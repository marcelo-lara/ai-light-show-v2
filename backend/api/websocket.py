from fastapi import WebSocket, WebSocketDisconnect
from typing import List
import json
import asyncio
from store.state import StateManager, FPS
from services.artnet import ArtNetService
from services.song_service import SongService
from pathlib import Path
import os

# Celery integration for analysis tasks (try backend package first)
try:
    from backend.tasks.celery_app import celery_app
    from backend.tasks.analyze import analyze_song as analyze_task
except Exception:
    try:
        from tasks.celery_app import celery_app
        from tasks.analyze import analyze_song as analyze_task
    except Exception:
        celery_app = None
        analyze_task = None

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
        status = await self.state_manager.get_status()
        initial_state = {
            "type": "initial",
            "fixtures": fixtures,
            "cues": cues,
            "song": song,
            "playback": {
                "fps": 60,
                "songLengthSeconds": getattr(self.state_manager, "song_length_seconds", 0.0),
                "isPlaying": status.get("isPlaying", False),
            },
            "status": status,
        }
        await websocket.send_json(initial_state)

    async def broadcast_status(self):
        await self.broadcast({"type": "status", "status": await self.state_manager.get_status()})

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

    async def _track_task_progress(self, task_id: str):
        """Poll Celery task meta and broadcast progress updates to all clients."""
        if celery_app is None:
            return

        # Configurable poll interval and timeout (seconds)
        poll_interval = float(os.environ.get("ANALYZE_TASK_POLL_INTERVAL", 0.5))
        timeout = int(os.environ.get("ANALYZE_TASK_TIMEOUT", 3600))

        try:
            last_state = None
            start = asyncio.get_event_loop().time()
            while True:
                # Safety: break if we've been polling too long
                elapsed = asyncio.get_event_loop().time() - start
                if elapsed > timeout:
                    await self.broadcast({"type": "task_error", "task_id": task_id, "message": "task tracking timeout"})
                    break

                try:
                    result = celery_app.AsyncResult(task_id)
                    state = result.state
                    info = result.info or {}
                except Exception as inner_exc:
                    # Transient failure talking to backend; report and retry
                    await self.broadcast({"type": "task_error", "task_id": task_id, "message": f"error reading task state: {inner_exc}"})
                    await asyncio.sleep(poll_interval)
                    continue

                # Broadcast only on state change or meta present
                if state != last_state or info:
                    try:
                        await self.broadcast({"type": "analyze_progress", "task_id": task_id, "state": state, "meta": info})
                    except Exception:
                        pass
                    last_state = state

                if state in ("SUCCESS", "FAILURE", "REVOKED"):
                    try:
                        final = celery_app.AsyncResult(task_id)
                        await self.broadcast({"type": "analyze_result", "task_id": task_id, "state": final.state, "result": getattr(final, 'result', None)})
                    except Exception:
                        pass
                    break

                await asyncio.sleep(poll_interval)
        except Exception as e:
            try:
                await self.broadcast({"type": "task_error", "task_id": task_id, "message": str(e)})
            except Exception:
                pass

    async def _watch_preview_completion(self, request_id: str):
        try:
            await self.state_manager.wait_for_preview_end(request_id)
            universe = await self.state_manager.get_output_universe()
            await self.artnet_service.update_universe(universe)
            await self.broadcast({
                "type": "preview_status",
                "active": False,
                "request_id": request_id,
            })
            await self.broadcast_status()
        except Exception:
            pass

    async def _stream_preview_to_artnet(self, request_id: str):
        try:
            while True:
                status = await self.state_manager.get_status()
                preview = status.get("preview") if isinstance(status, dict) else None
                if not status.get("previewActive"):
                    break
                if not isinstance(preview, dict):
                    break
                if str(preview.get("requestId") or "") != str(request_id):
                    break

                universe = await self.state_manager.get_output_universe()
                await self.artnet_service.update_universe(universe)
                await asyncio.sleep(1.0 / FPS)
        except Exception:
            pass

    async def handle_message(self, websocket: WebSocket, data: str):
        try:
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == "delta":
                if await self.state_manager.get_is_playing():
                    await websocket.send_json({"type": "delta_rejected", "reason": "playback_active"})
                    return

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
                await self.broadcast_status()

            elif msg_type == "preview_effect":
                result = await self.state_manager.start_preview_effect(
                    fixture_id=str(message.get("fixture_id") or ""),
                    effect=str(message.get("effect") or ""),
                    duration=float(message.get("duration") or 0.0),
                    data=message.get("data") or {},
                    request_id=message.get("request_id"),
                )

                if result.get("ok"):
                    universe = await self.state_manager.get_output_universe()
                    await self.artnet_service.update_universe(universe)
                    await self.broadcast({
                        "type": "preview_status",
                        "active": True,
                        "request_id": result.get("requestId"),
                        "fixture_id": result.get("fixtureId"),
                        "effect": result.get("effect"),
                        "duration": result.get("duration"),
                    })
                    asyncio.create_task(self._stream_preview_to_artnet(str(result.get("requestId") or "")))
                    asyncio.create_task(self._watch_preview_completion(str(result.get("requestId") or "")))
                else:
                    await websocket.send_json({
                        "type": "preview_status",
                        "active": False,
                        "reason": result.get("reason", "preview_rejected"),
                        "fixture_id": message.get("fixture_id"),
                        "effect": message.get("effect"),
                    })

                await self.broadcast_status()

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

            elif msg_type == "analyze_song":
                # Enqueue analyzer job via Celery and stream progress via task meta polling
                if analyze_task is None or celery_app is None:
                    await websocket.send_json({"type": "task_error", "message": "Analyzer not configured"})
                    return

                song_filename = message.get("filename")
                # Build absolute path to song file
                song_path = Path(self.song_service.songs_path) / f"{song_filename}.mp3"
                if not song_path.exists():
                    await websocket.send_json({"type": "task_error", "message": f"Song not found: {song_filename}"})
                    return

                # Submit Celery task
                task = analyze_task.apply_async(args=[str(song_path)], kwargs={
                    "device": message.get("device", "auto"),
                    "out_dir": str(self.song_service.metadata_path),
                    "temp_dir": message.get("temp_dir", "/app/temp_files"),
                    "overwrite": bool(message.get("overwrite", False)),
                })

                # Notify client
                await websocket.send_json({"type": "task_submitted", "task_id": task.id})

                # Start background progress streamer
                asyncio.create_task(self._track_task_progress(task.id))

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
