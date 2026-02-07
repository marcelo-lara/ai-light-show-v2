# Frontend — Architecture

The frontend is a Preact + Vite app responsible for:

- Audio playback (authoritative time source).
- Rendering waveform + timeline UI.
- Sending WebSocket messages to drive backend state.
- Displaying fixtures/cues and authoring edits.

## Key modules

- `frontend/src/App.jsx`: WebSocket connection + state store.
- `frontend/src/components/WaveformHeader.jsx`: WaveSurfer integration; sends `timecode`, `seek`, `playback`.
- `frontend/src/components/FixturesLane.jsx`: DMX sliders; sends `delta`.
- `frontend/src/components/CueSheetLane.jsx`: cue display and add-cue UX.
- `frontend/src/components/PlaybackControl.jsx`: always-visible compact playback overlay.

## WebSocket contract usage

Incoming:

- `initial`: fixtures, cues, song, playback state.
- `delta`: remote edits (broadcast).
- `dmx_frame`: paused seek-preview snapshots.
- `cues_updated`: updated cue sheet.
- `analyze_progress` / `analyze_result`: analyzer task status (optional UI consumption).

Outgoing:

- `delta`, `timecode`, `seek`, `playback`, `add_cue`, `load_song`, `chat`.

## Playback model

- The frontend audio timeline is authoritative.
- While playing, the backend is driven by periodic `timecode` updates.
- For seeks, the frontend sends `seek` immediately.
