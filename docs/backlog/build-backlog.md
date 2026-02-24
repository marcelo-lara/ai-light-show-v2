# AI Light Show - Build Backlog

Source of truth:
- `docs/ui/UX_User_Flow.md`
- `docs/ui/UI_Future_state.md`

This backlog intentionally ignores current code implementation details and defines the target product build plan.

## 1) Scope, assumptions, and definitions

### Product objective
Deliver an end-to-end workflow where a user can:
1. Prepare a song and metadata
2. Refine song timing metadata
3. Build a cue sheet with effects and chasers
4. Control fixtures and POIs in real time
5. Execute a synchronized show (audio + DMX)

### MVP assumptions
- Single operator session.
- Single selected song active at a time.
- One Art-Net target node for MVP.
- Playback lock policy: editing/preview actions that can conflict with playback are blocked while show playback is active.
- Time display format is dual: absolute time `mm:ss.mmmm` and musical position `bar.beat`.

### Timing and musical grid rules
- Canonical absolute time precision: `mm:ss.mmmm`.
- Canonical musical position: `bar.beat` (1-based bar index, 1-based beat index inside bar).
- Bar start is defined by each downbeat mark from metadata.
- Beats after a downbeat belong to that same bar until the next downbeat.
- If beat/downbeat metadata is incoherent or missing for a region, timing conversion falls back to global average BPM for that region.

### Priority labels
- `P0`: required for MVP demo.
- `P1`: required for reliable production-like use.
- `P2`: post-MVP hardening/usability.

### Story format
Each story includes:
- User story
- Acceptance criteria
- Dependencies
- Priority

## 2) Phase plan

## Phase 0 - Foundations and contracts
Goal: establish shared contracts, states, and quality gates before feature work.

### Epic FND-1: Domain model and file contracts

#### Story FND-1.1 (P0)
Status: unknown
User story: As a system, I need canonical JSON schemas for songs, sections, point hints, cues, chasers, POIs, and fixtures so all modules share one data contract.
Acceptance criteria:
- Schema docs exist for: song info, parts/sections, point hints, cue sheet entries, chaser definition, fixture profile, POI record.
- Required fields, optional fields, value ranges, and enum values are documented.
- Version field exists for persisted artifacts that may evolve.
Dependencies:
- None.

#### Story FND-1.2 (P0)
Status: unknown
User story: As a developer, I need validation rules for time and channel data so invalid show data cannot be saved.
Acceptance criteria:
- Validation rules documented for timestamp bounds, section start/end ordering, cue time validity, chaser offsets, DMX channel/value bounds.
- Error code list exists for validation failures.
Dependencies:
- FND-1.1.

#### Story FND-1.3 (P0)
Status: unknown
User story: As a system, I need deterministic time conversion between `mm:ss.mmmm` and `bar.beat` so editing and playback stay musically coherent.
Acceptance criteria:
- Conversion rules documented for `time -> bar.beat` and `bar.beat -> time`.
- Rule explicitly defines bar boundaries from metadata downbeats.
- Rule explicitly defines beat assignment inside each bar until next downbeat.
- Global average BPM fallback algorithm is documented for incoherent/missing beat-grid regions.
- Fallback activation criteria are documented and testable.
Dependencies:
- FND-1.1.

### Epic FND-2: Transport/event contract

#### Story FND-2.1 (P0)
Status: unknown
User story: As frontend and backend teams, we need a message/event catalog so real-time interactions are deterministic.
Acceptance criteria:
- Event catalog includes command, response, and error events for all flows.
- Payload examples exist for each event.
- Correlation field strategy defined for request/response matching.
Dependencies:
- FND-1.1.

#### Story FND-2.2 (P0)
Status: unknown
User story: As an operator, I need a consistent global playback state so every route behaves safely.
Acceptance criteria:
- Canonical playback states documented (`stopped`, `playing`, `paused`, `previewing`, `error`).
- Allowed transitions and rejection reasons are defined.
- Lock/disable matrix exists for edit actions by state.
Dependencies:
- FND-2.1.

### Epic FND-3: Cross-cutting UX and observability

#### Story FND-3.1 (P1)
Status: unknown
User story: As a user, I need consistent save/dirty/error behavior so I do not lose work.
Acceptance criteria:
- Shared UX rules documented for dirty indicators, save success, save failure, retry, and unsaved-change exit prompts.
- Rules apply to sections, point hints, cues, chasers, and POIs.
Dependencies:
- FND-1.2.

#### Story FND-3.2 (P1)
Status: unknown
User story: As QA/support, I need structured logs and diagnostics so sync and runtime issues are debuggable.
Acceptance criteria:
- Logging spec includes correlation ID, song ID, cue/chaser IDs, playback state transitions, preview start/stop, and Art-Net output lifecycle.
- User-visible error status model documented.
Dependencies:
- FND-2.1.

Phase exit criteria:
- Data schemas complete.
- Event/state contract complete.
- Validation/error model complete.
- `mm:ss.mmmm <-> bar.beat` conversion and BPM fallback rules complete.

## Phase 1 - Preparation and Song Analysis
Goal: metadata readiness and precise timing edit workflow.

### Epic ANL-1: Preparation readiness and song loading

#### Story ANL-1.1 (P0)
Status: unknown
User story: As a user, I need startup readiness checks so I know whether I can begin analysis.
Acceptance criteria:
- Song Analysis entry state shows `Song available`, `Metadata available`, `Ready for editing`.
- If metadata missing, UI blocks downstream actions and shows remediation steps.
Dependencies:
- FND-1.1, FND-2.1.

#### Story ANL-1.2 (P0)
Status: unknown
User story: As a user, I need to load/select a song context so all pages operate on the same song.
Acceptance criteria:
- Global selected-song state exists.
- Song switch updates analysis/builder/dmx/show pages consistently.
- Switching songs with unsaved changes triggers confirmation.
Dependencies:
- ANL-1.1, FND-3.1.

### Epic ANL-2: Section editing

#### Story ANL-2.1 (P0)
Status: unknown
User story: As a user, I can create/edit/delete section labels on a waveform timeline.
Acceptance criteria:
- User can add section with label and time range.
- User can modify label/start/end.
- User can delete section.
- Invalid overlaps/ranges are blocked with error feedback.
Dependencies:
- FND-1.2.

#### Story ANL-2.2 (P0)
Status: unknown
User story: As a user, I can save section edits and trust persistence.
Acceptance criteria:
- Dirty state appears after any section edit.
- Save persists data and clears dirty state.
- Failed save preserves edits and shows retry path.
Dependencies:
- ANL-2.1, FND-3.1.

### Epic ANL-3: Point hints editing

#### Story ANL-3.1 (P0)
Status: unknown
User story: As a user, I can add/edit/delete point hints at exact positions.
Acceptance criteria:
- Supported hint operations: create, move, relabel, delete.
- Timestamp precision is millisecond-level.
- Out-of-bounds timestamps are blocked.
Dependencies:
- FND-1.2.

#### Story ANL-3.2 (P1)
Status: unknown
User story: As a user, I can filter and quickly navigate point hints.
Acceptance criteria:
- Hint list can filter by label/type.
- Selecting hint seeks waveform cursor to hint time.
Dependencies:
- ANL-3.1.

### Epic ANL-4: Navigation and transport tooling

#### Story ANL-4.1 (P1)
Status: unknown
User story: As a user, I can navigate by beat/section for precise edits.
Acceptance criteria:
- Controls exist for previous/next beat and previous/next section.
- Seeking keeps UI time indicators in sync.
- UI shows both `mm:ss.mmmm` and `bar.beat` for the current cursor position.
Dependencies:
- ANL-1.2, FND-1.3.

#### Story ANL-4.2 (P1)
Status: unknown
User story: As a user, I can trust timing navigation even when beat/downbeat metadata is incoherent.
Acceptance criteria:
- When incoherent beat-grid regions are detected, UI uses global average BPM fallback for `bar.beat` estimation.
- Fallback state is visible in analysis status.
- Returning to coherent metadata automatically exits fallback mode.
Dependencies:
- ANL-4.1, FND-1.3.

Phase exit criteria:
- User can complete metadata preparation without manual JSON editing.
- Sections and hints are safely persisted with validation.
- Analysis timeline exposes reliable `bar.beat` with BPM fallback when needed.

## Phase 2 - Show Builder (cue authoring)
Goal: build cue sheets with effect and chaser entries anchored to timeline.

### Epic BLD-1: Cue sheet data model and timeline operations

#### Story BLD-1.1 (P0)
Status: unknown
User story: As a user, I can create and view cue entries on a timeline.
Acceptance criteria:
- Cue entry includes: ID, timecode, target fixture/group, action type (effect/chaser), params, duration.
- Cue list and timeline views stay synchronized.
- Cue timeline displays both `mm:ss.mmmm` and `bar.beat` positions.
Dependencies:
- FND-1.1, FND-1.3, FND-2.1.

#### Story BLD-1.2 (P0)
Status: unknown
User story: As a user, I can edit/remove/reposition cues with precise timecode.
Acceptance criteria:
- Cue time can be changed numerically and by timeline interaction.
- Cue delete and undo-last-action are supported.
- Invalid times are blocked.
- Editing by `bar.beat` updates absolute `mm:ss.mmmm` consistently using the timing conversion rules.
Dependencies:
- BLD-1.1, FND-1.3.

### Epic BLD-2: Effect picker workflow

#### Story BLD-2.1 (P0)
Status: unknown
User story: As a user, I can add an effect cue by selecting fixture, effect, parameters, and duration.
Acceptance criteria:
- Effect picker shows only valid effects for selected fixture type.
- Required params enforced before add.
- Added cue appears at current cursor time or specified time.
Dependencies:
- BLD-1.1, FND-1.2.

#### Story BLD-2.2 (P0)
Status: unknown
User story: As a user, I can preview effect before committing to cue sheet.
Acceptance criteria:
- Preview action executes without persisting a cue.
- Preview can be canceled.
- Preview is blocked while show playback is active.
Dependencies:
- BLD-2.1, FND-2.2.

### Epic BLD-3: Chaser picker and chaser creation

#### Story BLD-3.1 (P0)
Status: unknown
User story: As a user, I can add a chaser cue with optional parameters.
Acceptance criteria:
- Chaser picker lists available chasers.
- Parameter form validates input.
- Adding creates a chaser cue entry at selected time.
Dependencies:
- BLD-1.1.

#### Story BLD-3.2 (P0)
Status: unknown
User story: As a user, I can save selected cues as a new chaser using relative offsets.
Acceptance criteria:
- User can multi-select cues and invoke `Save as Chaser`.
- First selected cue stored as offset `0`; others as positive offsets.
- New chaser becomes available in picker.
Dependencies:
- BLD-1.2, BLD-3.1.

#### Story BLD-3.3 (P1)
Status: unknown
User story: As a user, I can choose chaser scope (song-local or global).
Acceptance criteria:
- Scope selection is explicit at save time.
- Scope metadata persists and is enforced in picker visibility.
Dependencies:
- BLD-3.2.

### Epic BLD-4: Cue validation and conflict handling

#### Story BLD-4.1 (P1)
Status: unknown
User story: As a user, I get immediate feedback for invalid cue configurations.
Acceptance criteria:
- Validation catches unsupported effect params, invalid fixture refs, invalid durations, and illegal overlaps when policy forbids them.
- User receives actionable message with field-level context.
Dependencies:
- BLD-2.1, BLD-3.1.

Phase exit criteria:
- Operator can author a complete cue sheet from timeline.
- Effects/chasers can be previewed then committed.
- Chasers can be created from cue selections.

## Phase 3 - DMX Controller and POI workflow
Goal: robust real-time fixture control independent of cue authoring.

### Epic DMX-1: Manual fixture control

#### Story DMX-1.1 (P0)
Status: unknown
User story: As a user, I can control fixture channels from fixture-specific panels.
Acceptance criteria:
- Supported fixture card types exist (moving head, RGB/par, generic fallback).
- Channel writes are bounded to valid DMX range.
- UI reflects last acknowledged state.
Dependencies:
- FND-1.1, FND-2.1.

#### Story DMX-1.2 (P1)
Status: unknown
User story: As a user, I see clear disable states during playback lock.
Acceptance criteria:
- Controls disabled based on lock matrix.
- Disabled reason tooltip/status is visible.
Dependencies:
- FND-2.2.

### Epic DMX-2: Effect preview in DMX controller

#### Story DMX-2.1 (P0)
Status: unknown
User story: As a user, I can preview a fixture effect with parameters and duration.
Acceptance criteria:
- Preview payload includes fixture ID, effect name, duration, params.
- Backend executes preview path and returns status.
- Preview never persists to cue sheet.
Dependencies:
- DMX-1.1, FND-2.1.

#### Story DMX-2.2 (P1)
Status: unknown
User story: As a user, preview lifecycle is deterministic.
Acceptance criteria:
- Preview can be started/stopped.
- Starting show playback cancels active preview.
- Preview failure state surfaces reason.
Dependencies:
- DMX-2.1, FND-2.2.

### Epic DMX-3: POI management (moving heads)

#### Story DMX-3.1 (P0)
Status: unknown
User story: As a user, I can recall POI position on click.
Acceptance criteria:
- Clicking POI sends move command to recorded pan/tilt.
- UI shows active POI and completion/failure state.
Dependencies:
- DMX-1.1.

#### Story DMX-3.2 (P0)
Status: unknown
User story: As a user, I can record POI using SHIFT+click.
Acceptance criteria:
- SHIFT+click stores current pan/tilt into target POI slot.
- Save confirmation visible.
- Persisted POIs remain available after reload.
Dependencies:
- DMX-3.1, FND-3.1.

Phase exit criteria:
- Real-time manual control and preview are operational.
- POI recall/record works reliably for moving heads.

## Phase 4 - Show Control and synchronization
Goal: authoritative show execution with synchronized audio/DMX timeline.

### Epic SHW-1: Playback orchestration

#### Story SHW-1.1 (P0)
Status: unknown
User story: As an operator, I can start and stop show playback reliably.
Acceptance criteria:
- Play triggers DMX stream start and host audio playback start sequence.
- Stop halts DMX stream safely and updates global state.
- Transport controls are debounced against duplicate rapid clicks.
Dependencies:
- FND-2.2, BLD-1.1.

#### Story SHW-1.2 (P0)
Status: unknown
User story: As an operator, playback state propagates to all pages.
Acceptance criteria:
- All routes reflect same authoritative playback status.
- Lock policy applies instantly when state changes.
Dependencies:
- SHW-1.1.

### Epic SHW-2: Time synchronization and drift handling

#### Story SHW-2.1 (P0)
Status: unknown
User story: As an operator, server playback time stays synchronized with host play time.
Acceptance criteria:
- Sync mechanism and heartbeat defined.
- Measured drift value is available in diagnostics.
- If drift exceeds threshold, system corrects or alerts.
- Runtime diagnostics expose both current `mm:ss.mmmm` and derived `bar.beat`.
Dependencies:
- SHW-1.1, FND-1.3, FND-3.2.

#### Story SHW-2.2 (P1)
Status: unknown
User story: As an operator, I receive clear sync health status.
Acceptance criteria:
- UI displays sync state (`healthy`, `degraded`, `lost`).
- Recovery behavior defined for transient disconnect.
Dependencies:
- SHW-2.1.

### Epic SHW-3: Runtime safety and failure handling

#### Story SHW-3.1 (P1)
Status: unknown
User story: As an operator, failures fail-safe rather than producing undefined output.
Acceptance criteria:
- Failure policies defined for Art-Net disconnect, audio host failure, and malformed cue payload.
- Emergency stop behavior documented and tested.
Dependencies:
- SHW-1.1.

Phase exit criteria:
- End-to-end show can run from authored cues.
- Sync behavior and failure states are observable and controlled.

## Phase 5 - Hardening, UX polish, and release readiness
Goal: production-grade reliability and operator confidence.

### Epic REL-1: Performance and scale envelope

#### Story REL-1.1 (P1)
Status: unknown
User story: As an operator, I need predictable runtime performance under realistic load.
Acceptance criteria:
- Load profiles defined (fixture count, cue density, preview frequency).
- Latency and jitter measurements captured against target thresholds.
- Regressions tracked in CI reports.
Dependencies:
- SHW-2.1.

### Epic REL-2: Data lifecycle and migrations

#### Story REL-2.1 (P1)
Status: unknown
User story: As a maintainer, I can evolve persisted schema safely.
Acceptance criteria:
- Schema migration strategy documented.
- Backward-compatibility behavior defined for previous metadata versions.
- Migration test fixtures exist.
Dependencies:
- FND-1.1.

### Epic REL-3: Operator usability and resilience

#### Story REL-3.1 (P2)
Status: unknown
User story: As an operator, I can recover quickly from common workflow mistakes.
Acceptance criteria:
- Undo/redo strategy defined for analysis and builder actions.
- Confirmation patterns used for destructive actions.
- Inline help/tooltips for critical controls.
Dependencies:
- ANL-2.2, BLD-1.2.

Phase exit criteria:
- Quality gates pass.
- Known high-severity defects resolved.
- Release checklist complete.

## 3) QA plan hints (for test strategy and backlog linking)

## QA-1 Test layers
- Unit tests: schema validation, time math, `mm:ss.mmmm <-> bar.beat` conversion, downbeat/beat grouping, global average BPM fallback logic, parameter validators, offset conversion, playback state reducer.
- Integration tests: API/event contracts, persistence, preview lifecycle, lock policy behavior.
- End-to-end tests: full user workflows across pages and shared state.
- Hardware-in-the-loop tests: Art-Net output behavior on representative fixtures.

## QA-2 Core end-to-end scenarios
1. Preparation happy path
- Song available + metadata available -> Song Analysis ready.

2. Song Analysis edit/save
- Edit sections and point hints -> save -> reload -> data persists exactly.

3. Builder authoring happy path
- Add effect cue + add chaser cue + save selected cues as chaser -> chaser reusable.

4. Preview non-persistence
- Run preview in Builder/DMX -> verify no cue mutation unless explicitly added.

5. Playback lock policy
- Start show -> editing/preview blocked where required -> stop -> controls re-enabled.

6. Show sync baseline
- Play show -> monitor host/server drift -> verify threshold behavior.

7. POI workflow
- Record POI with SHIFT+click -> recall POI -> verify pan/tilt target reached.

8. Failure handling
- Simulate Art-Net disconnect/audio failure -> verify user-visible error and safe behavior.

9. Incoherent timing metadata fallback
- Corrupt/remove beat-grid region -> verify `bar.beat` still advances via global average BPM fallback and fallback state is visible.

## QA-3 Non-functional checks
- Timing precision checks for timeline edits and cue trigger times in both `mm:ss.mmmm` and `bar.beat`.
- Throughput tests for high cue density.
- Stability tests for long playback sessions.
- Recovery tests for reconnect/reload during active sessions.

## QA-4 Regression suite gates by phase
- Phase 1 gate: analysis CRUD and persistence pass.
- Phase 2 gate: cue/chaser authoring + preview semantics pass.
- Phase 3 gate: DMX control/preview/POI pass.
- Phase 4 gate: full playback and sync pass.
- Phase 5 gate: performance/stability thresholds pass.

## QA-5 Defect severity policy (recommended)
- `S0`: unsafe output or unrecoverable playback failure.
- `S1`: major workflow blocked, no workaround.
- `S2`: partial feature degradation with workaround.
- `S3`: cosmetic or low-impact issue.

Release blocker rule:
- No open `S0` or `S1` defects for MVP release candidate.

## 4) Backlog maintenance rules

- Every story must map to one user goal in `UX_User_Flow.md`.
- Every story must include acceptance criteria before implementation starts.
- Contract changes require synchronized updates to schema docs, event catalog, and QA cases.
- Any change to beat/downbeat interpretation must update `mm:ss.mmmm <-> bar.beat` conversion rules and fallback tests.
- Any new runtime state must include lock policy and error handling behavior.
- Completed stories must attach evidence: test IDs, logs/screenshots, and updated docs.
