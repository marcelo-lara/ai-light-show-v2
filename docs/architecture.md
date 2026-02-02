# AI Light Show v2 — Architecture

This document describes the current architecture of AI Light Show v2.

The system is a real-time DMX control application synchronized to audio playback. The frontend owns audio playback time; the backend renders a **precomputed DMX canvas** (60 FPS) from an **action-based cue sheet**, and outputs the correct DMX frame for the current audio position.

## Goals

- **Deterministic lighting playback** tied to audio time.
- **Seek correctness**: seeking to any song time immediately selects the correct DMX state (frame skipping allowed).
- **Fixture-specific effect logic**: each fixture type owns its channel calculations for actions like `flash` and `move_to`.
- **Simple persistence**: cue sheets and metadata are JSON files.

## Repository Layout (relevant parts)

- backend/
  - main.py — FastAPI app lifecycle (startup loads fixtures/song; starts Art-Net sender)
  - api/websocket.py — the only control plane (WebSocket protocol)
  - services/
    - artnet.py — Art-Net UDP sender (60 FPS)
    - song_service.py — song discovery + metadata helpers
  - store/
    - state.py — StateManager: fixtures, cue sheet, editor/output universes, DMX canvas, playback state
    - dmx_canvas.py — memory-efficient canvas buffer
  - models/
    - cue.py — cue sheet models (action-based)
    - song.py — song + metadata models
    - fixtures/
      - fixture.py — Fixture base class + action rendering contract
      - parcan.py — Parcan-specific action rendering
      - moving_head.py — MovingHead-specific action rendering

- frontend/
  - src/App.jsx — WebSocket client + state
  - src/components/WaveformHeader.jsx — WaveSurfer playback + timecode/seek/playback messages
  - src/components/FixturesLane.jsx — DMX authoring sliders + “Add to Cue”
  - src/components/CueSheetLane.jsx — displays cues (by time)

## Core Concepts

### 1) Cue Sheet (action-based)

Cue sheets are **high-level instructions**, not per-channel snapshots.

**File location**
- `backend/cues/{song}.cue.json`

**Schema** (see `backend/models/cue.py`)
- `CueSheet`
  - `song_filename: str`
  - `entries: list[CueEntry]`

- `CueEntry`
  - `time: float` — cue start time in seconds
  - `fixture_id: str` — fixture to act on
  - `action: str` — action name (e.g. `set_channels`, `flash`, `move_to`)
  - `duration: float` — seconds the action lasts
  - `data: dict` — action parameters (fixture-dependent)
  - `name: str | null` — optional label

**Important behavior**
- The current authoring UI (“plain control”) records **`set_channels`** actions per fixture.
- Additional actions (e.g. `flash`, `move_to`) are supported by the renderer and should be authored by future UI controls.

### 2) DMX Canvas (precomputed)

The DMX canvas is a **precomputed** sequence of DMX universes at 60 FPS for the full song length.

- Canvas FPS: `60`
- Universe size: `512` channels
- Max song length: **6 minutes** (360 seconds)

**Memory estimate**
- Frames ≈ `(song_seconds * 60) + 1`
- Bytes ≈ `frames * 512`
- For 6 minutes: `21601 frames * 512 ≈ 11,059,712 bytes` (~10.6 MiB) stored as a single `bytearray`.

Implementation details (see `backend/store/dmx_canvas.py`)
- Frames are stored contiguously in one `bytearray`:
  - `buffer[frame_index*512 : (frame_index+1)*512]`

### 3) Two universes: editor vs output

StateManager holds two separate DMX universes:

- **editor_universe**: reflects live slider edits (authoring state).
- **output_universe**: what is actually sent to Art-Net.

This allows the play-state routing policy:
- **Not playing (paused / edit mode)**: Art-Net output follows the frontend **Fixtures lane** (live `delta` edits update both `editor_universe` and `output_universe`).
- **Playing (playback mode)**: Art-Net output follows the **DMX canvas** (timecode/seek selects a canvas frame and overwrites `output_universe`). Live `delta` edits still update `editor_universe` but do **not** affect `output_universe`.

### 4) Fixture-specific action rendering

Each fixture type implements an action renderer (see `backend/models/fixtures/fixture.py`):

`render_action(universe, action, frame_index, start_frame, end_frame, fps, data, render_state)`

- The renderer is called during canvas generation for every active cue and frame.
- `render_state` is a per-entry dict that fixtures can use to cache values (e.g., a `move_to` start position).

Current implementations:
- `Parcan`
  - `set_channels` (instant)
  - `flash` (fade down across duration; defaults to RGB if present)
- `MovingHead`
  - `set_channels` (instant)
  - `move_to` (interpolates pan/tilt; supports degrees → byte conversion via `meta` ranges)
  - `flash` (dimmer-only, if present)

## Runtime Flow

### Startup

1. Backend loads fixtures from `backend/fixtures/fixtures.json`.
2. Backend “arms” fixtures by applying their `arm` values to the universes.
3. Backend starts the Art-Net sender loop (60 FPS). It repeatedly sends the **current output_universe**.
4. Backend loads the default song (if present) and builds the DMX canvas.
5. Backend syncs frame 0 to Art-Net.

### Song load

WebSocket message: `{"type":"load_song", "filename":"..."}`

Backend:
- Loads metadata and cue sheet for the song.
- Computes song length seconds from metadata (prefers explicit duration if added later; otherwise derives from parts/hints/drums; clamps at 6 minutes).
- Builds a new DMX canvas.
- Resets timecode to 0.
- Broadcasts new initial state.

### Playback (timecode-driven)

Frontend is authoritative for time. It sends:

- `{"type":"playback", "playing": true|false}` on play/pause
- `{"type":"timecode", "time": <seconds>}` periodically **while playing** (throttled)
- `{"type":"seek", "time": <seconds>}` immediately on seek

Backend:
- Maps time to canvas frame: `frame = round(time * fps)`.
- Sets `output_universe = canvas[frame]`.
- Art-Net sender emits that universe at 60 FPS.

**Paused behavior**
- While **not playing**, the backend ignores `timecode` updates (so paused timecode sync does not drive Art-Net).
- A `seek` while **not playing** acts as a **preview**: the backend selects the nearest canvas frame, updates its current time, applies the frame to `output_universe`, and sends that frame back to the frontend so the Fixtures lane sliders reflect the previewed values.

**Skipping policy**
- If audio time jumps forward/back, backend **does not** simulate intermediate frames.
- It simply selects the correct frame for the reported time.

### Authoring cues (Add to Cue)

Frontend sends:
- `{"type":"add_cue", "time": <seconds>, "name": "optional"}`

Backend records cue entries:
- Currently generates one `set_channels` entry **per fixture** capturing the editor universe for the fixture’s channel map.
- Persists cue sheet JSON.

Re-render policy:
- If playing: marks canvas dirty (actions are recorded, not rendered live).
- If not playing: immediately rebuilds the canvas from the updated cue sheet.

## WebSocket Protocol (current)

### Backend → Frontend

- `initial`
  - `fixtures`: array
  - `cues`: full cue sheet
  - `song`: song + metadata
  - `playback`: `{ fps, songLengthSeconds, isPlaying }`

- `delta`
  - `{ type:'delta', channel, value }`

- `dmx_frame`
  - `{ type:'dmx_frame', time, values }`
  - `values` is a JSON array of ints (0–255) representing channels `[1..N]`, truncated to the **max channel used by fixtures** to keep payloads small.
  - Sent on connect (to reflect armed defaults in the Fixtures lane) and on **paused seek-preview**. Not streamed during playback.

- `cues_updated`
  - `{ type:'cues_updated', cues: <CueSheet> }`

### Frontend → Backend

- `delta` — live DMX edits (`channel` is 1-based)
- `timecode` — current audio time (seconds)
- `seek` — explicit seek/jump to time (seconds)
- `playback` — playing state
- `add_cue` — record actions at the given time
- `load_song` — load a different song
- `chat` — mock echo

## Art-Net Output

See `backend/services/artnet.py`.

- Sends ArtDMX packets to the configured node IP/port.
- Runs a loop at ~60 FPS.
- Only logs packet slices when DMX output changes.

## Known Limitations / Next Steps

- The authoring UI currently only creates `set_channels` actions. Adding UI controls for `flash`, `move_to`, color changes, etc. will make the cue sheet truly “effect-based”.
- Canvas rebuild while playing is intentionally deferred (canvas marked dirty). A future `rebuild_canvas` message could allow an explicit “re-render now” workflow.
- Multi-client sync is not implemented; current assumptions are single controlling client.
