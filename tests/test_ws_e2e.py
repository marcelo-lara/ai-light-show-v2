import asyncio
import json
from pathlib import Path
import pytest

from backend.api.websocket import WebSocketManager
from backend.tasks.celery_app import celery_app
from backend.tasks.analyze import analyze_song


class FakeWS:
    def __init__(self):
        self.sent = []

    async def send_json(self, message):
        self.sent.append(message)


class FakeSongService:
    def __init__(self, songs_path: Path, metadata_path: Path):
        self.songs_path = songs_path
        self.metadata_path = metadata_path


class DummyState:
    # minimal stub used only to satisfy WebSocketManager constructor
    def __init__(self):
        self.fixtures = []
        self.cue_sheet = None
        self.current_song = None


class DummyArtNet:
    async def update_universe(self, universe):
        return None


@pytest.mark.asyncio
async def test_websocket_enqueues_task_and_receives_progress(tmp_path):
    # Prepare fake song file
    songs_dir = tmp_path / "songs"
    metadata_dir = tmp_path / "metadata"
    songs_dir.mkdir()
    metadata_dir.mkdir()
    song_file = songs_dir / "test_song.mp3"
    song_file.write_text("dummy")

    # Create manager with stubs
    manager = WebSocketManager(DummyState(), DummyArtNet(), FakeSongService(str(songs_dir), str(metadata_dir)))

    # Prepare websocket and register as active connection
    ws = FakeWS()
    manager.active_connections.append(ws)

    # Configure Celery to run tasks eagerly and use in-memory backend
    celery_app.conf.task_always_eager = True
    celery_app.conf.result_backend = 'cache+memory://'
    celery_app.conf.broker_url = 'memory://'

    # Send analyze_song message
    msg = json.dumps({"type": "analyze_song", "filename": "test_song", "device": "auto", "temp_dir": str(tmp_path / 'temp'), "overwrite": False})
    await manager.handle_message(ws, msg)

    # Allow background tracker to poll once
    await asyncio.sleep(0.2)

    # Assert we received a task_submitted and at least one progress or result
    types = [m.get('type') for m in ws.sent]
    assert 'task_submitted' in types
    assert any(t in types for t in ('analyze_progress', 'analyze_result'))
