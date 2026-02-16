# Features Backlog (Prioritized)

This file is a product/engineering backlog: it defines *what* we want to build and in what order.
It intentionally does **not** include implementation details.

## Goals
- Make song selection + playback feel like a cohesive “show control” app.
- Add authoring tools for reusable lighting building blocks (POIs, chasers/scenes).

## Guiding constraints (current architecture)
- Backend currently exposes only a WebSocket at `/ws` (no REST yet).
- Playback output uses a precomputed 60 FPS DMX canvas rendered from effect-based cues.
- During playback, live “delta” edits are ignored for output.

---

## Roadmap

### Phase 1 — Navigation + Song Loading (highest priority)

#### 1) Always-Visible Playback Control (bottom-right)
Add a playback control that is always visible across the app (all sections).

Placement and layout (per ![LoFi](<../LoFi Always-Visible Playback Control.png>)):
- **Pinned to the bottom-right** of the page as an **overlay**.
- Shows:
	- Song name
	- Current position and total song length (e.g. `00.000 | 120.457`)
	- Progress bar (position)
	- Play/Stop button

Acceptance criteria:
- Control remains visible while switching sections.
- Control reflects the currently loaded song and playback state.

#### 2) Frontend Section Menu
Add a section selector (icons) to switch between the main areas.

Sections:
- **Show Control**: current main UI, playback + cue authoring.
- **DMX Controller**: CRUD for chasers, scenes, and POI mappings.

Acceptance criteria:
- Switching sections does not break playback state unexpectedly.
- Each section has a clear empty/loading state.

#### 3) POI Designer
UI to manage Points of Interest (POIs) and map fixture pan/tilt values to a POI.

Scope:
- POI list: create/update/delete.
- Fixture list.
- When a fixture is selected: show a “fixture panel” to pan/tilt the physical fixture to the POI position, then save mapping: `fixture pan/tilt values -> POI`.

Acceptance criteria:
- POIs can be created and persist across reload.
- A fixture can be mapped to a POI and the mapping persists.

Dependencies:
- Store POIs + mappings in a global JSON file under `backend/fixtures/` (exact filename/schema to be defined).
- Define how the “fixture panel” sends pan/tilt commands (live deltas vs a dedicated message).

#### 4) Song Selection
When the user clicks the song name, show a list of available songs (from `backend/songs`). Selecting a song loads it in the UI and triggers the backend to rebuild/re-render the DMX canvas for that song.

Acceptance criteria:
- Song list populates from the backend’s available songs.
- Selecting a song updates the UI state and backend state (song + cues + canvas) consistently.
- The current song is always clearly indicated.

Dependencies:
- Backend needs a way to list songs and load a specific song (message type and payload to be defined).

---

### Phase 2 — Authoring Tools (DMX Controller)

#### 7) Chaser Designer
UI to manage reusable chasers.

Scope:
- Chaser list: create/update/delete.
- On select: timeline editor with fixtures/effects.
- Persist chasers in `backend/fixtures/chasers.json`.

Acceptance criteria:
- Chasers persist and can be reloaded.
- Timeline edits produce a stable, validated chaser definition.

Dependencies:
- Define the chaser schema (effects, timing model, fixture addressing).
- Chasers are authoring primitives that compile into the existing effect-based cue model.

---

## Later / Stretch

### 8) Show Plan Generation
Add a button to generate a show plan:
- Generate cues for a segment of the song (effect-based cues for a time range), OR
- Generate a plan for the whole song (storytelling instructions per segment).

Acceptance criteria:
- The output format is explicit (where it’s stored and how it is applied).
- Segment-based generation does not corrupt existing cues unintentionally.

Dependencies:
- Decide how “plan” maps to cues and how edits are reviewed/applied.

---

## Decisions (confirmed)
- POIs + fixture mappings are stored globally under `backend/fixtures/`.
- Chasers/scenes compile into the existing effect-based cue sheet.
