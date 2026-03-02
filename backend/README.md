# Backend Module (LLM Guide)

FastAPI + asyncio runtime responsible for real-time DMX state management and Art-Net output.

## Purpose

- Serve the single WebSocket control plane at `/ws`.
- Maintain fixture state, cue sheets, playback status, and precomputed DMX canvas.
- Stream DMX output continuously via Art-Net.

## Primary entrypoints

- `main.py`: app startup, service wiring, lifecycle.
- `api/websocket.py`: message handling and broadcast logic.
- `store/state.py`: source of truth for fixtures, song, cues, preview/playback state.
- `store/dmx_canvas.py`: flat byte-buffer DMX frame storage.
- `services/artnet.py`: UDP Art-Net frame transmission.
- `services/song_service.py`: song/meta listing utilities.

## Runtime model

1. On startup, backend loads fixtures/POIs/cues, arms fixtures, starts Art-Net, and loads default song if available.
2. Song load builds a precomputed 60 FPS DMX canvas for the full song window.
3. A control client sends timeline and authoring messages via WebSocket.
4. Backend updates output universe and Art-Net stream based on playback state.

## WebSocket protocol essentials

### Client → Backend

- `hello`: handshake, requesting a fresh snapshot.
- `intent`: backend-routed intent envelope with `{req_id, name, payload}`.
	- Supported names include transport (`transport.play|pause|stop|jump_to_time`),
		fixture (`fixture.set_arm|set_values|preview_effect`), and
		LLM (`llm.send_prompt|cancel`).

### Backend → Client

- `snapshot`: full authoritative state + `seq`.
- `patch`: event-driven state changes + `seq` and list of `{path, value}` updates.
- `event`: info/warning/error notifications (including LLM stream chunks).

## Data and file contracts

- Fixtures: `backend/fixtures/fixtures.json`
- POIs: `backend/fixtures/pois.json`
- Cues: `backend/cues/{song}.cue.json`
- Songs: `backend/songs/*.mp3`
- Metadata root in Docker: `/app/meta` (mounted from `analyzer/meta`)

## Invariants and constraints

- DMX channels are 1-based externally; internal storage is 0-based 512-byte universe.
- While playing, `delta` edits are rejected.
- Preview effects are non-persistent and must not mutate cue files.
- Keep initialization and teardown safe (blackout on shutdown).

## Development

```bash
cd backend
pip install -r requirements.txt
python main.py
```

Default local URL: `http://localhost:5001`.

## LLM contributor checklist

1. Preserve message compatibility unless intentionally changing protocol.
2. Update client state handling when protocol fields change.
3. Keep cue/effect behavior deterministic at 60 FPS.
4. If fixture effect contracts change, update protocol documentation and active client implementation in the same PR.
