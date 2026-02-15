from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from store.state import StateManager
from services.artnet import ArtNetService
from services.song_service import SongService
from api.websocket import WebSocketManager, websocket_endpoint

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize services
    backend_path = Path(__file__).parent
    
    # Use absolute paths for Docker containers, relative for local development
    songs_path = Path("/app/songs") if Path("/app/songs").exists() else backend_path / "songs"
    metadata_path = Path("/app/metadata") if Path("/app/metadata").exists() else backend_path / "metadata"
    cues_path = Path("/app/cues") if Path("/app/cues").exists() else backend_path / "cues"

    artnet_debug = os.getenv("ARTNET_DEBUG", "0").strip().lower() in {"1", "true", "yes", "on"}
    artnet_debug_file = os.getenv("ARTNET_DEBUG_FILE") or None
    
    state_manager = StateManager(backend_path, songs_path, cues_path, metadata_path)
    artnet_service = ArtNetService(debug=artnet_debug, debug_file=artnet_debug_file)
    song_service = SongService(songs_path, metadata_path)
    ws_manager = WebSocketManager(state_manager, artnet_service, song_service)

    # Startup
    fixtures_path = backend_path / "fixtures" / "fixtures.json"
    pois_path = backend_path / "fixtures" / "pois.json"
    await state_manager.load_pois(pois_path)
    await state_manager.load_fixtures(fixtures_path)
    # Arm fixtures
    for fixture in state_manager.fixtures:
        await artnet_service.arm_fixture(fixture)
    # Start ArtNet
    await artnet_service.start()
    # Load first song if available
    songs = song_service.list_songs()
    target_song = 'sono - keep control'
    if target_song in songs:
        await state_manager.load_song(target_song)
    elif songs:
        await state_manager.load_song(songs[0])

    # Sync initial output universe (frame 0) to Art-Net.
    try:
        await artnet_service.update_universe(await state_manager.get_output_universe())
    except Exception as e:
        print(f"Error syncing initial universe: {e}")

    # Initial ArtNet sequence: left-to-right blue wipe that lasts exactly 1 second.
    # Behavior: first half = turn ON left→right; second half = turn OFF left→right.
    parcans_with_blue = sorted(
        [f for f in state_manager.fixtures if f.id.startswith('parcan') and 'blue' in f.channels],
        key=lambda f: f.location.get('x', 0)
    )
    total_duration = 1.0
    if parcans_with_blue:
        n = len(parcans_with_blue)
        # Single fixture: keep lit for the whole duration then turn off at the end.
        if n == 1:
            parcan = parcans_with_blue[0]
            channel_num = parcan.channels['blue']
            await artnet_service.set_channel(channel_num, 255)
            await asyncio.sleep(total_duration)
            await artnet_service.set_channel(channel_num, 0)
        else:
            phase = total_duration / 2.0
            spacing = phase / (n - 1)
            # Turn ON left-to-right over the first half
            for i, parcan in enumerate(parcans_with_blue):
                channel_num = parcan.channels['blue']
                await artnet_service.set_channel(channel_num, 255)
                if i < n - 1:
                    await asyncio.sleep(spacing)
            # Turn OFF left-to-right over the second half
            for i, parcan in enumerate(parcans_with_blue):
                channel_num = parcan.channels['blue']
                await artnet_service.set_channel(channel_num, 0)
                if i < n - 1:
                    await asyncio.sleep(spacing)

    # Make services available to routes
    app.state.state_manager = state_manager
    app.state.artnet_service = artnet_service
    app.state.song_service = song_service
    app.state.ws_manager = ws_manager

    yield

    # Shutdown: perform blackout so fixtures go dark, then stop the Art-Net service
    try:
        await artnet_service.blackout()
    except Exception as e:
        print(f"Error during blackout: {e}")
    await artnet_service.stop()

app = FastAPI(lifespan=lifespan, title="AI Light Show v2 Backend")

# Serve audio files - use absolute path for Docker, relative for local development
songs_directory = Path("/app/songs") if Path("/app/songs").exists() else Path(__file__).parent / "songs"
app.mount("/songs", StaticFiles(directory=songs_directory), name="songs")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend URL
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