from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.intents.llm.cue_edit_api import router as llm_cue_edit_router
from api.intents.llm.cue_sheet_context import build_cue_sheet_payload
from api.intents.llm.intent_catalog import build_intent_catalog_payload
from api.intents.llm.playback_context import build_playback_position_payload
from api.intents.llm.show_context import build_cue_section_payload, build_cue_window_payload
from api.intents.llm.song_context import (
	build_fixture_detail_payload,
	build_fixture_inventory_payload,
	build_song_context_payload,
	build_song_sections_payload,
)
from api.intents.llm.timing_context import build_section_at_time_payload, build_section_by_name_payload
from api.websocket import WebSocketManager, websocket_endpoint
from services.artnet import ArtNetService
from services.song_service import SongService
from services.startup_animation import run_startup_blue_wipe
from store.state import StateManager


logging.basicConfig(
	level=logging.DEBUG if os.getenv("DEBUG", "0") in ("1", "true", "yes", "on") else logging.INFO,
	format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
	backend_path = Path(__file__).parent
	songs_path = Path("/app/songs") if Path("/app/songs").exists() else backend_path / "songs"
	meta_path = Path("/app/meta") if Path("/app/meta").exists() else backend_path / "meta"
	cues_path = Path("/app/cues") if Path("/app/cues").exists() else backend_path / "cues"

	debug_mode = os.getenv("DEBUG_MODE", "0").strip().lower() in {"1", "true", "yes", "on"}
	debug_file = os.getenv("DEBUG_FILE") or os.getenv("ARTNET_DEBUG_FILE") or None

	state_manager = StateManager(backend_path, songs_path, cues_path, meta_path)
	artnet_service = ArtNetService(debug=debug_mode, debug_file=debug_file)
	song_service = SongService(songs_path, meta_path)
	ws_manager = WebSocketManager(state_manager, artnet_service, song_service)

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
	yield

	await ws_manager.stop_playback_ticker()
	try:
		await artnet_service.blackout()
	except Exception:
		logger.exception("Failed during blackout on shutdown")
	await artnet_service.stop()


app = FastAPI(lifespan=lifespan, title="AI Light Show v2 Backend")
app.include_router(llm_cue_edit_router)

songs_directory = Path("/app/songs") if Path("/app/songs").exists() else Path(__file__).parent / "songs"
app.mount("/songs", StaticFiles(directory=songs_directory), name="songs")

meta_directory = Path("/app/meta") if Path("/app/meta").exists() else Path(__file__).parent / "meta"
app.mount("/meta", StaticFiles(directory=meta_directory), name="meta")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.get("/")
async def root():
	return {"message": "AI Light Show v2 Backend"}


@app.get("/llm/context/song")
async def llm_song_context():
	return {"ok": True, "data": build_song_context_payload(app.state.ws_manager)}


@app.get("/llm/context/playback")
async def llm_playback_context():
	return {"ok": True, "data": await build_playback_position_payload(app.state.ws_manager)}


@app.get("/llm/context/fixtures")
async def llm_fixtures_context():
	return {"ok": True, "data": {"fixtures": build_fixture_inventory_payload(app.state.ws_manager)}}


@app.get("/llm/context/fixtures/{fixture_id}")
async def llm_fixture_detail_context(fixture_id: str):
	detail = build_fixture_detail_payload(app.state.ws_manager, fixture_id)
	if detail is None:
		return {"ok": False, "error": {"reason": "fixture_not_found", "fixture_id": fixture_id}}
	return {"ok": True, "data": detail}


@app.get("/llm/context/sections")
async def llm_sections_context():
	return {"ok": True, "data": build_song_sections_payload(app.state.ws_manager)}


@app.get("/llm/context/intents")
async def llm_intents_context():
	return {"ok": True, "data": build_intent_catalog_payload()}


@app.get("/llm/context/cues/current")
async def llm_current_cues_context():
	return {"ok": True, "data": build_cue_sheet_payload(app.state.ws_manager)}


@app.get("/llm/context/sections/by-name/{section_name}")
async def llm_section_by_name_context(section_name: str):
	detail = build_section_by_name_payload(app.state.ws_manager, section_name)
	if detail is None:
		return {"ok": False, "error": {"reason": "section_not_found", "section_name": section_name}}
	return {"ok": True, "data": detail}


@app.get("/llm/context/sections/at-time")
async def llm_section_at_time_context(time_s: float):
	detail = build_section_at_time_payload(app.state.ws_manager, time_s)
	if detail is None:
		return {"ok": False, "error": {"reason": "section_not_found", "time_s": time_s}}
	return {"ok": True, "data": detail}


@app.get("/llm/context/cues/window")
async def llm_cue_window_context(start_s: float, end_s: float):
	return {"ok": True, "data": build_cue_window_payload(app.state.ws_manager, start_s, end_s)}


@app.get("/llm/context/cues/section/{section_name}")
async def llm_cue_section_context(section_name: str):
	detail = build_cue_section_payload(app.state.ws_manager, section_name)
	if detail is None:
		return {"ok": False, "error": {"reason": "section_not_found", "section_name": section_name}}
	return {"ok": True, "data": detail}


@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
	await websocket_endpoint(websocket, app.state.ws_manager)


if __name__ == "__main__":
	import uvicorn

	uvicorn.run(app, host="0.0.0.0", port=5001)
