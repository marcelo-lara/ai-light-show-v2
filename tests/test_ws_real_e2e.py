import os
import sys
import time
import json
import socket
import subprocess
import asyncio
import pytest


REAL = os.environ.get("REAL_E2E", "0") == "1"


def _redis_available(host: str, port: int = 6379, timeout: float = 1.0) -> bool:
    try:
        s = socket.create_connection((host, port), timeout)
        s.close()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not REAL, reason="Real E2E disabled (set REAL_E2E=1)")
def test_ws_real_e2e(tmp_path):
    # Require a reachable Redis instance
    redis_host = os.environ.get("REDIS_HOST", "localhost")
    redis_port = int(os.environ.get("REDIS_PORT", "6379"))
    if not _redis_available(redis_host, redis_port, timeout=2.0):
        pytest.skip(f"Redis not available at {redis_host}:{redis_port}")

    # Ensure Celery env is set to use the real Redis
    broker = f"redis://{redis_host}:{redis_port}/0"
    env = os.environ.copy()
    env["CELERY_BROKER_URL"] = broker
    env["CELERY_RESULT_BACKEND"] = broker
    env["PYTHONPATH"] = env.get("PYTHONPATH", "") + ":./backend"

    # Start a Celery worker process
    worker_cmd = [sys.executable, "-m", "celery", "-A", "backend.tasks.celery_app.celery_app", "worker", "--loglevel=info", "--concurrency=1"]
    proc = subprocess.Popen(worker_cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        # allow worker to start
        time.sleep(5)

        # Now import modules and run the same flow as the in-process E2E test
        from backend.api.websocket import WebSocketManager
        from backend.tasks.celery_app import celery_app

        # Minimal stubs
        class DummyState:
            fixtures = []
            cue_sheet = None
            current_song = None

        class DummyArtNet:
            async def update_universe(self, universe):
                return None

        class FakeWS:
            def __init__(self):
                self.sent = []

            async def send_json(self, message):
                self.sent.append(message)

        class FakeSongService:
            def __init__(self, songs_path, metadata_path):
                self.songs_path = songs_path
                self.metadata_path = metadata_path

        songs_dir = tmp_path / "songs"
        metadata_dir = tmp_path / "metadata"
        songs_dir.mkdir()
        metadata_dir.mkdir()
        (songs_dir / "real_song.mp3").write_text("x")

        manager = WebSocketManager(DummyState(), DummyArtNet(), FakeSongService(str(songs_dir), str(metadata_dir)))
        ws = FakeWS()
        manager.active_connections.append(ws)

        # Do not set celery eager; we want the real worker to process the job
        # Submit analyze_song message
        msg = json.dumps({"type": "analyze_song", "filename": "real_song", "device": "auto", "temp_dir": str(tmp_path / 'temp'), "overwrite": False})
        # Run handler
        asyncio.get_event_loop().run_until_complete(manager.handle_message(ws, msg))

        # Wait for some progress/result (max 60s)
        deadline = time.time() + 60
        seen_progress = False
        while time.time() < deadline:
            types = [m.get('type') for m in ws.sent]
            if 'task_submitted' in types:
                if any(t in types for t in ('analyze_progress', 'analyze_result')):
                    seen_progress = True
                    break
            time.sleep(0.5)

        assert seen_progress, f"No progress/result received, messages: {ws.sent}"

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()