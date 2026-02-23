# AI Light Show - UI Future State

This document defines the target UI vision aligned to `docs/ui/UX_User_Flow.md` (source of truth).

## Product intent

The UI must support a production workflow from preparation to show execution with precise timecode control:

1. Preparation
2. Song Analysis
3. Show Builder
4. DMX Controller
5. Show Control

## UX principles

- Time precision first: all editing actions are anchored to exact song timecode.
- Safe playback model: no conflicting live edits while show playback is active.
- Fast iteration: preview before commit for effects and chasers.
- Reusable programming: users can convert cue selections into reusable chasers.
- Hardware-aware control: fixture behavior must map clearly to Art-Net/DMX output.

## Navigation and app shell (target)

- Main routes:
  - `/analysis` - Song Analysis
  - `/builder` - Show Builder
  - `/dmx` - DMX Controller
  - `/show` - Show Control
- Primary flow order in navigation: Song Analysis -> Show Builder -> DMX Controller -> Show Control.
- Startup entry for new sessions: Song Analysis (after preparation).
- Global song context is shared across all routes.
- Global playback status is visible and consistent across all routes.

## Preparation (outside UI + entry conditions)

### User goal
- Provide a song and generated analysis metadata before editing/programming.

### Required conditions
- Song file exists in `/backend/songs`.
- Analyzer script has produced metadata used by UI pages.

### UI behavior
- Song Analysis must show explicit readiness state:
  - `Song available`
  - `Metadata available`
  - `Ready for editing`
- If metadata is missing, UI provides clear guidance and blocks downstream programming actions.

## Song Analysis (target state)

### User goal
- Adjust song metadata and exact timecode data used by cue programming.

### Required capabilities
- Waveform-based editing for song sections:
  - Create/edit/delete section labels.
  - Adjust section start and end times.
  - Save changes to metadata.
- Song point hints management:
  - Create/edit/delete point hints (for example: clap, hey, drop).
  - Set exact position on waveform/timeline.
  - Save changes to metadata.
- Transport and navigation controls to move by beats/sections.
- Metadata status surface with dirty/saved/error state.

### Behavior rules
- Unsaved changes are clearly indicated.
- Save action persists both sections and point hints.
- Validation prevents invalid time ranges or out-of-bounds timestamps.

## Show Builder (target state)

### User goal
- Build and manage the cue sheet for the selected song.

### Required capabilities
- Timecode-aware cue authoring:
  - Move song cursor to target time.
  - Add effect cue from Effect Picker:
    - Select fixture
    - Select effect
    - Set optional parameters
    - Preview effect
    - Commit to cue sheet
  - Add chaser cue from Chaser Picker:
    - Select chaser
    - Set optional parameters
    - Preview chaser
    - Commit to cue sheet
- Cue sheet editing:
  - Select one or more cues
  - Edit/remove/reposition cues with exact timecode
- Save as Chaser:
  - Create a chaser from selected cues
  - Persist with relative offsets where first selected cue is `t=0`
  - Make chaser reusable in current song and globally (based on system scope settings)

### Behavior rules
- Preview is non-persistent until user commits.
- Cue conflicts or invalid parameters are surfaced immediately.
- Builder state remains synchronized with song timeline.

## DMX Controller (target state)

### User goal
- Control fixtures in real time, preview effects, and manage moving-head POIs.

### Required capabilities
- Per-fixture manual control panels that stream Art-Net frames on change.
- Fixture effect preview:
  - Select effect
  - Set optional parameters and duration
  - Run preview
  - Render preview on DMX canvas and output to Art-Net node
- POI management for moving heads:
  - Click POI to recall recorded position
  - SHIFT+click POI to record current pan/tilt as that POI

### Behavior rules
- Manual control and preview respect global playback lock policy.
- Preview remains non-persistent (does not change cue sheet unless explicitly added in Show Builder).
- POI interactions give clear visual confirmation for recall/record states.

## Show Control (target state)

### User goal
- Start and stop the light show playback with synchronized audio and DMX output.

### Required capabilities
- Play/Stop controls for show execution.
- On play:
  - Pre-rendered DMX canvas/frames are sent to Art-Net node.
  - Music plays on host.
  - Server time is synchronized to host play time.
- On stop:
  - DMX playback stream stops safely.
  - Playback state resets or pauses per system policy.

### Behavior rules
- Playback state is authoritative and propagated to all routes.
- Sync drift and transport errors are visible to user with actionable status.

## Cross-page consistency requirements

- Shared selected-song context across all pages.
- Shared transport/playback state across all pages.
- Consistent time display format and timecode precision.
- Consistent save/dirty/error patterns for all editable entities.
- Predictable disable rules while playback is active.

## Out of scope for this document

- Visual design system details (colors, typography, spacing).
- Low-level backend protocol definitions.
- Final implementation details of internal state management.

## Relationship to current docs

- `docs/ui/UX_User_Flow.md`: source of truth for workflow and user goals.
- `docs/ui/UI.md`: current implementation snapshot.
- `docs/ui/UI_Future_state.md` (this file): target UI behavior aligned to source-of-truth flow.
