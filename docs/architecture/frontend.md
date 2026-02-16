# Frontend — Architecture

The frontend is a Preact + Vite app responsible for:

- Audio playback (authoritative time source).
- Rendering waveform + timeline UI.
- Sending WebSocket messages to drive backend state.
- Displaying fixtures/cues and authoring edits.

The UI is a routed, persistent 3-column app shell:

- Left: icon-only navigation
- Center: routed page content
- Right: always-visible Player + Chat

## Key modules

- `frontend/src/App.jsx`: mounts the app shell + router.
- `frontend/src/app/state.jsx`: WebSocket connection, shared state, and outbound actions.
- `frontend/src/layout/AppShell.jsx`: 3-column layout.
- `frontend/src/layout/RightPanel.jsx`: right panel wiring (player + chat).

Pages:

- `frontend/src/pages/ShowControlPage.jsx`: waveform + lanes.
- `frontend/src/pages/DmxControllerPage.jsx`: placeholder.
- `frontend/src/pages/ShowBuilderPage.jsx`: placeholder.

Core components:

- `frontend/src/components/layout/LeftMenu.jsx`: icon-only left navigation.
- `frontend/src/components/player/WaveformHeader.jsx`: WaveSurfer integration and timecode emission.
- `frontend/src/components/player/PlayerPanel.jsx`: always-visible player UI (right panel).
- `frontend/src/components/chat/ChatSidePanel.jsx`: local chat history + outbound `chat` message.
- `frontend/src/components/lanes/FixturesLane.jsx`: DMX sliders; sends `delta`.
- `frontend/src/components/lanes/CueSheetLane.jsx`: cue display.
- `frontend/src/components/lanes/SongPartsLane.jsx`: song part display (from metadata when present).

## WebSocket contract usage

Incoming:

- `initial`: fixtures, cues, song, playback state.
- `delta`: remote edits (broadcast).
- `dmx_frame`: paused seek-preview snapshots.
- `cues_updated`: updated cue sheet.
- Other message types may exist server-side, but the frontend currently only consumes the above.

Outgoing:

- `delta`, `timecode`, `seek`, `playback`, `chat`.

## Playback wiring

- The WaveSurfer instance lives in `WaveformHeader` (center column) and is the authoritative audio engine.
- The always-visible `PlayerPanel` (right panel) controls playback by calling app actions:
	- `actions.togglePlay()`
	- `actions.seekTo(time)`
- `WaveformHeader` registers audio controls via `actions.registerAudioControls(...)` so the right panel can control WaveSurfer even though it is rendered elsewhere.
- If the audio controls are not registered (e.g., before WaveSurfer initializes), the actions fall back to sending `playback` / `seek` messages to the backend.

## Playback model

- The frontend audio timeline is authoritative.
- While playing, the backend is driven by periodic `timecode` updates.
- For seeks, the frontend sends `seek` immediately.

Implementation notes:

- `WaveformHeader` emits timecode at ~20 Hz while playing (throttled) and emits `playback` changes on play/pause.
- There are no playback buttons in the waveform header; the right-panel player is the single playback control surface.
