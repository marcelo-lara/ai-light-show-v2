from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio
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
    state_manager = StateManager(backend_path)
    artnet_service = ArtNetService()
    song_service = SongService(backend_path / "songs", backend_path / "metadata")
    ws_manager = WebSocketManager(state_manager, artnet_service, song_service)

    # Startup
    fixtures_path = backend_path / "fixtures" / "fixtures.json"
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

    # Initial ArtNet sequence: flash blue on parcans
    parcans = [f for f in state_manager.fixtures if f.id.startswith('parcan')]
    for parcan in parcans:
        if 'blue' in parcan.channels:
            channel_num = parcan.channels['blue']
            await artnet_service.set_channel(channel_num, 255)
            await asyncio.sleep(0.3)
            await artnet_service.set_channel(channel_num, 0)
            await asyncio.sleep(0.3)

    # Make services available to routes
    app.state.state_manager = state_manager
    app.state.artnet_service = artnet_service
    app.state.song_service = song_service
    app.state.ws_manager = ws_manager

    yield

    # Shutdown
    await artnet_service.stop()

app = FastAPI(lifespan=lifespan, title="AI Light Show v2 Backend")

# Serve audio files
backend_path = Path(__file__).parent
app.mount("/songs", StaticFiles(directory=backend_path / "songs"), name="songs")

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