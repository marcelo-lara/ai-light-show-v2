import asyncio
import json
from pathlib import Path
from services.artnet import ArtNetService
from store.state import StateManager
from services.song_service import SongService
from api.websocket import WebSocketManager
from api.state.fixtures import build_fixtures_payload

async def main():
    backend_path = Path('.')
    songs_path = Path('/app/songs')
    cues_path = Path('/app/cues')
    meta_path = Path('/app/meta')
    sm = StateManager(backend_path, songs_path, cues_path, meta_path)
    await sm.load_fixtures(backend_path / 'fixtures' / 'fixtures.json')
    asrv = ArtNetService()
    ssrv = SongService(songs_path, meta_path)
    wm = WebSocketManager(sm, asrv, ssrv)
    universe = bytearray(512)
    payload = build_fixtures_payload(wm, universe)
    print(json.dumps(payload, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
