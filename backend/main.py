from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from pathlib import Path
from store.state import StateManager
from services.artnet import ArtNetService
from services.song_service import SongService
from api.websocket import WebSocketManager, websocket_endpoint

app = FastAPI(title="AI Light Show v2 Backend")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
backend_path = Path(__file__).parent
state_manager = StateManager(backend_path)
artnet_service = ArtNetService()
song_service = SongService(backend_path / "songs", backend_path / "metadata")
ws_manager = WebSocketManager(state_manager, artnet_service, song_service)

@app.on_event("startup")
async def startup_event():
    # Load fixtures
    fixtures_path = Path(__file__).parent / "fixtures" / "fixtures.json"
    await state_manager.load_fixtures(fixtures_path)
    # Arm fixtures
    for fixture in state_manager.fixtures:
        await artnet_service.arm_fixture(fixture)
    # Start ArtNet
    await artnet_service.start()

@app.on_event("shutdown")
async def shutdown_event():
    await artnet_service.stop()

@app.get("/")
async def root():
    return {"message": "AI Light Show v2 Backend"}

@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    await websocket_endpoint(websocket, ws_manager)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)