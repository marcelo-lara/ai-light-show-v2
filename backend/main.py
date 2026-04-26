from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import os
import logging
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path
from models.song import resolve_meta_root, resolve_songs_root
from store.pois import PoiStore
from store.state import StateManager
from services.artnet import ArtNetService
from services.assistant import AssistantService
from services.song_service import SongService
from services.startup_animation import run_startup_blue_wipe
from api.websocket import WebSocketManager, websocket_endpoint
from mcp_server import BackendMcpRuntime, create_backend_mcp

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG", "0") in ("1", "true", "yes", "on") else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

backend_mcp_runtime = BackendMcpRuntime()
backend_mcp = create_backend_mcp(backend_mcp_runtime)
backend_mcp_app = backend_mcp.http_app(
    path="/",
    stateless_http=True,
    json_response=True,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:
        mcp_lifespan = getattr(backend_mcp_app, "lifespan", None)
        if mcp_lifespan is not None and not os.environ.get("PYTEST_CURRENT_TEST"):
            await stack.enter_async_context(mcp_lifespan(app))

        backend_path = Path(__file__).parent
        songs_path = resolve_songs_root(backend_path)
        meta_path = resolve_meta_root(backend_path)
        cues_path = Path("/app/cues") if Path("/app/cues").exists() else backend_path / "cues"

        debug_mode = os.getenv("DEBUG_MODE", "0").strip().lower() in {"1", "true", "yes", "on"}
        debug_file = os.getenv("DEBUG_FILE") or os.getenv("ARTNET_DEBUG_FILE") or None

        state_manager = StateManager(backend_path, songs_path, cues_path, meta_path)
        artnet_service = ArtNetService(debug=debug_mode, debug_file=debug_file)
        song_service = SongService(songs_path, meta_path)
        ws_manager = WebSocketManager(state_manager, artnet_service, song_service)
        assistant_service = AssistantService(backend_path)

        fixtures_path = backend_path / "fixtures" / "fixtures.json"
        pois_path = backend_path / "fixtures" / "pois.json"
        await state_manager.load_pois(pois_path)
        await state_manager.load_fixtures(fixtures_path)
        for fixture in state_manager.fixtures:
            await artnet_service.arm_fixture(fixture)
        await artnet_service.start()

        songs = song_service.list_songs()
        target_song = "Yonaka - Seize the Power"
        if target_song in songs:
            await state_manager.load_song(target_song)
        elif songs:
            await state_manager.load_song(songs[0])

        try:
            await artnet_service.update_universe(await state_manager.get_output_universe())
        except Exception:
            logger.exception("Failed to sync initial output universe")

        await run_startup_blue_wipe(state_manager, artnet_service)

        app.state.state_manager = state_manager
        app.state.artnet_service = artnet_service
        app.state.song_service = song_service
        app.state.ws_manager = ws_manager
        app.state.assistant_service = assistant_service
        app.state.backend_mcp = backend_mcp
        ws_manager.assistant_service = assistant_service
        backend_mcp_runtime.attach(ws_manager, song_service)

        try:
            yield
        finally:
            backend_mcp_runtime.clear()
            await ws_manager.stop_playback_ticker()
            try:
                await artnet_service.blackout()
            except Exception:
                logger.exception("Failed during blackout on shutdown")
            await artnet_service.stop()

app = FastAPI(lifespan=lifespan, title="AI Light Show v2 Backend")
app.state.backend_mcp = backend_mcp
app.mount("/mcp", backend_mcp_app, name="mcp")

# Serve audio files - use absolute path for Docker, relative for local development
songs_directory = resolve_songs_root(Path(__file__).parent)
app.mount("/songs", StaticFiles(directory=songs_directory), name="songs")

# Serve song metadata artifacts (plots/chords/json)
meta_directory = resolve_meta_root(Path(__file__).parent)
app.mount("/meta", StaticFiles(directory=meta_directory), name="meta")

# CORS for browser-based control clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed client origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "AI Light Show v2 Backend"}

@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    await websocket_endpoint(websocket, app.state.ws_manager)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)
