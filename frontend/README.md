# AI Light Show v2 — Frontend

This frontend is a Deno-served TypeScript browser client. It renders backend-authoritative state from WebSocket `snapshot`/`patch` messages and emits user `intent` messages.

UI layout references live in [../docs/ui/README.md](../docs/ui/README.md).

## Source of truth

- Code is authoritative over docs.
- Primary entrypoints:
  - `frontend/dev.ts` (dev server + bundle + HTML shell rendering)
  - `frontend/src/app/main.ts` (boot + mount)
  - `frontend/src/app/boot.ts` (state hydration + WS lifecycle)
  - `frontend/src/app/AppShell.ts` (layout + route rendering)
  - `frontend/src/shared/transport/protocol.ts` (message/types contract)

## Runtime and behavior model

1. `main.ts` resolves WebSocket URL and calls `boot({ wsUrl })`, then mounts `AppShell`.
2. `boot.ts` initializes theme, hydrates state from `window.__BOOTSTRAP_STATE__` or `localStorage.last_snapshot`, connects `WsClient`, and sends `hello`.
3. Inbound WS messages:
   - `snapshot`: replace store via `applySnapshot`.
   - `patch`: apply sequence-ordered path/value changes via `applyPatch`.
   - `event`: route LLM streaming chunks/messages to `llm_state`; backend errors become chat system messages.
  - `cue_helper_apply_failed` surfaces missing artifact filenames and paths for `song_draft` failures.
4. `AppShell.ts` renders `Sidebar + Main + RightPanel`, rerenders on UI/Backend/LLM store updates, and refreshes the singleton song player.
5. Timecode sync exception: browser playback time is authoritative during playback and syncs via `transport.jump_to_time`.

Time display convention:
- Show song-position and cue-time values in `s.mmm` format across the UI.
- Current transport/cue editing flows continue to use numeric milliseconds or seconds in data payloads where required, but displayed values should stay normalized to `s.mmm`.
- If backend-formatted time strings are introduced later, they should use the same `s.mmm` display convention.

## Active route map (actual code)

Route definitions live in `src/app/routes.ts` and `src/shared/state/ui_state.ts`.

| Route id | Sidebar label | View function | Current behavior |
| --- | --- | --- | --- |
| `show_control` | Show Control | `ShowControlView()` | Renders `SongPlayer()` with `SongSectionsPanel`, a placeholder cue summary panel, and a placeholder fixture-effects panel |
| `song_analysis` | Song Analysis | `SongAnalysisView()` | Renders `SongPlayer()` with Song Loader plus the shared chord panel, Song Events plus an inert Event Tools placeholder, chord-pattern mining cards, and analysis plot panels in a four-column layout |
| `show_builder` | Show Builder | `ShowBuilderView()` | Renders `SongPlayer()` with the shared chord progression panel, live cue sheet, effect picker, chaser picker, and cue helpers |
| `dmx_control` | DMX Control | `DmxControlView()` | Renders fixture grid with dynamic controls |

`features/home/HomeView.ts` exists but is not wired into current route state or sidebar.

Default local route state is `song_analysis` when nothing is stored in `localStorage.ui_route`.

## Protocol and intent surface

Protocol types and intent names are defined in `src/shared/transport/protocol.ts`.

Client -> backend message types:
- `hello`
- `intent`

Backend -> client message types:
- `snapshot`
- `patch`
- `event`

Intent names currently emitted by frontend:
- Song: `song.list`, `song.load`
- Transport: `transport.play`, `transport.pause`, `transport.stop`, `transport.jump_to_time`, `transport.jump_to_section`
- Fixture: `fixture.set_arm`, `fixture.set_values`, `fixture.preview_effect`
- Cue: `cue.add`, `cue.update`, `cue.delete`, `cue.clear`, `cue.apply_helper`
- Chaser: `chaser.apply`, `chaser.preview`, `chaser.stop_preview`, `chaser.start`, `chaser.stop`, `chaser.list`
- LLM: `llm.send_prompt`, `llm.cancel`
- POI: `poi.update_fixture_target`

Protocol includes additional names (`fixture.stop_preview`, `poi.create`, `poi.update`, `poi.delete`) for compatibility with backend contracts.

Frontend cue/chaser payload expectations:
- `state.cues` is a mixed list of cue entries:
  - effect cue: `time`, `fixture_id`, `effect`, `duration`, `data`, optional `name`, optional `created_by`
  - chaser cue: `time`, `chaser_id`, `data`, optional `name`, optional `created_by`
- `state.chasers` entries include stable `id`, display `name`, `description`, and beat-based `effects`.
- `state.fixtures.<id>.supported_effects` is a list of effect descriptors with `id`, `name`, `description`, `tags`, and `schema`.
- Frontend effect selectors and preview controls must use `supported_effects[].id` as the effect value and `supported_effects[].name` as the visible label.
- Chaser intents use `chaser_id` in payloads, not `chaser_name`.
- Chaser cue repetitions live in `cue.data.repetitions`.

## State stores and global bridges

Store modules:
- `src/shared/state/backend_state.ts`: authoritative backend snapshot/patch store (`stale`, `seq`, `state`).
- `src/shared/state/ui_state.ts`: local route + selected fixture id.
- `src/shared/state/theme_state.ts`: persisted theme (`dark`, `tokyo-dark`, `light`).
- `src/features/llm_chat/llm_state.ts`: local chat transcript + streaming buffer.

Global bridge fields used across modules:
- `__WS_CLIENT__`: connected `WsClient` instance
- `__WS_STATE__`: current connection state
- `__LLM_STATE__`: mirror of local LLM status for `StatusCard`
- `__BACKEND_HTTP_ORIGIN__`: derived from WS URL for resolving relative audio URLs

## Frontend code map (exports and responsibilities)

### App shell and boot
- `src/app/main.ts`: app bootstrap entry.
- `src/app/boot.ts`: `boot(ctx)` + hydration + WS event dispatch.
- `src/app/AppShell.ts`: `mountAppShell(root)` + route/main/right panel rerender policy. The right panel always renders `StatusCard()` and `LlmChatView()`.
- `src/app/routes.ts`: `ROUTES` metadata for sidebar buttons.
- `src/app/server.ts`: `renderDocument()` HTML shell with CSS includes + bootstrap injection.

### Shared transport/state
- `src/shared/transport/ws_client.ts`: `WsClient` reconnecting WebSocket client.
- `src/shared/transport/protocol.ts`: all backend/frontend protocol types.
- `src/shared/transport/supported_effects.ts`: helpers that normalize `FixtureState.supported_effects` descriptors into effect ids and dropdown options.
- `src/shared/transport/transport_intents.ts`: transport intent senders.
- `src/shared/state/backend_state.ts`: snapshot/patch reducer and subscribers.
- `src/shared/state/song_data.ts`: cleaned song chord/section selectors shared by analysis and builder views.
- `src/shared/state/selectors.ts`: UI-safe selectors (`show_state`, lock, playback, fixtures, arm count).
- `src/shared/state/ui_state.ts`: route selection/persistence.
- `src/shared/state/theme_state.ts`: theme init/apply/persistence.

### Shared musical structure panel
- `src/shared/components/chords_panel/ChordsPanel.ts`: section-based chord progression card shared by song analysis and show builder.
- `src/shared/components/chords_panel/grouping.ts`: groups chord changes by song section boundaries (`start_s/end_s`).
- `src/shared/components/chords_panel/render.ts`: section block rendering helper.
- `src/shared/components/chords_panel/types.ts`: panel/group type contracts.
- `src/shared/components/chords_panel/ChordsPanel.css`: shared styling for the chord progression card.

### Song player (shared across routes)
- `src/shared/components/song_player/SongPlayer.ts`: singleton facade (`SongPlayer`, `refreshSongPlayer`).
- `src/shared/components/song_player/SongPlayerController.ts`: orchestration class for playback, navigation, looping, region rebuild, backend sync.
- `src/shared/components/song_player/ui/buildSongPlayerUi.ts`: UI composition extracted from controller lifecycle logic.
- `src/shared/components/song_player/logic/WaveSurferManager.ts`: WaveSurfer lifecycle, regions plugin, media controls.
- `src/shared/components/song_player/logic/PlaybackSync.ts`: backend sync cadence (10s periodic + debounced seeks + immediate sync).
- `src/shared/components/song_player/logic/song_logic.ts`: section/beat utilities, canonical beat-type normalization, and song fingerprinting.
- `src/shared/components/song_player/logic/navigation_loop.ts`: pure section/beat navigation and loop-wrap target helpers.
- `src/shared/components/song_player/logic/song_player_state.ts`: song identity/data derivation, paused playback time normalization, audio URL resolution.
- `src/shared/components/song_player/logic/wave_callbacks.ts`: WaveSurfer callback orchestration bindings for controller state updates.
- `src/shared/components/song_player/logic/regions.ts`: section/downbeat overlay generation driven by canonical beat events.
- `src/shared/components/song_player/ui/*`: waveform, transport buttons, readout, options, layout primitives.

### Show Control
- `src/features/show_control/ShowControlView.ts`: composes song player + show-control panels.
- `src/features/show_control/components/SongSectionsPanel.ts`: renders backend `song.sections` and sends `transport.jump_to_section` on row activation.
- `SongSectionsPanel` highlight rule uses section bounds with a small start-time tolerance (`start_s - 0.01`): active when `timeS > (start_s - 0.01) && timeS < end_s`.

### Song Analysis
- `src/features/song_analysis/SongAnalysisView.ts`: composes player with a four-column analysis layout: `SongLoaderPanel()` plus shared `ChordsPanel()` in column one, `SongEventsPanel()` plus the inert Event Tools placeholder in column two, chord-pattern mining cards in column three, and analysis plot cards in column four.
- `src/features/song_analysis/song_analysis_state.ts`: derives cleaned/sorted beats, analysis plots, song-event timeline data, and chord-pattern mining data from backend state and composes shared song structure data.
- `src/features/song_analysis/song_loader/SongLoaderPanel.ts`: event-driven available-song list with confirmation before `song.load`.
- `src/features/song_analysis/song_loader/state.ts`: local song-loader store fed by `song_list` events.
- `src/features/song_analysis/analyzer_queue/AnalyzerQueuePanel.ts`: placeholder analysis queue panel. It reads the inert backend `state.analyzer` payload and keeps the layout stable without sending queue intents.
- `src/features/song_analysis/analyzer_queue_models.ts`: queue-state display labels used by the placeholder panel.
- `src/features/song_analysis/chord_patterns/ChordPatterns.ts`: chord-pattern mining model and active-occurrence helpers for Song Analysis.
- `src/features/song_analysis/chord_patterns/ChordPatternsPanel.ts`: scrollable pattern-card column with occurrence squares sourced from `analysis.patterns[]`.
- `src/features/song_analysis/song_events/SongEvents.ts`: song-event timeline model and active-window logic for Song Analysis.
- `src/features/song_analysis/song_events/SongEventsPanel.ts`: scrollable song-event card list with playback-synced `is-active` highlighting.
- `src/features/song_analysis/components/BeatTable.ts`: beat grouping panel for canonical beat events, including explicit beat/downbeat type.

`BeatTable.ts` exists but is not mounted by the current `SongAnalysisView()`.

### Show Builder
- `src/features/show_builder/ShowBuilderView.ts`: composes player with the shared chord progression card, `CueSheet()`, and `FlowColumn()`.
- `src/features/show_builder/cue_intents.ts`: cue/chaser intent senders (`addCue`, `updateCue`, `deleteCue`, `clearCues`, `applyCueHelper`, chaser apply/preview/start/stop/list helpers). Chaser helpers send `chaser_id`.
- `src/features/show_builder/cue_utils.ts`: cue type guards and shared cue/chaser helpers for labels, repetitions, duration, and signatures.
- `src/features/show_builder/components/cue_sheet/CueSheet.ts`: live cue list panel, subscribes to backend `cues` state and emits cue edit/preview/delete/select actions. Delete confirmation names the selected cue type, label, and time.
- `src/features/show_builder/components/flow_column/FlowColumn.ts`: composes `EffectPicker()`, `ChaserPicker()`, and `CueHelpers()`.
- `src/features/show_builder/components/effect_picker/EffectPicker.ts`: fixture/effect selection panel for effect cue rows only — assembles DOM, wires events, manages subscription.
- `src/features/show_builder/components/effect_picker/layout.ts`: DOM builders for top row, parameter section, and action row; returns typed ref objects.
- `src/features/show_builder/components/effect_picker/updates.ts`: stateful DOM updaters (`applyEffectOptions`, `applyFixtureOptions`, `renderParamForm`).
- `src/features/show_builder/components/effect_picker/selectors.ts`: backend state reads and `formatTime` helper.
- `src/features/show_builder/components/effect_picker/types.ts`: `PickerState` type.
- `src/features/show_builder/components/effect_params/params_schema.ts`: effect parameter definitions for dynamic form generation.
- `src/features/show_builder/components/effect_params/ParamForm.ts`: renders parameter inputs based on effect schema.
- `src/features/show_builder/components/chaser_picker/ChaserPicker.ts`: chaser selection and chaser cue editing. The picker shows the individual chaser effects for reference/preview, but `Add` and `Update` persist a single cue row with `chaser_id` plus `data.repetitions`.
- `src/features/show_builder/components/cue_helpers/CueHelpers.ts`: backend-driven helper selector with dynamic parameter fields and a bottom `Apply` action.

Show Builder current cue-sheet behavior:
- Cue sheet rows render one of two layouts:
  - effect cue row: `time / fixture / effect / duration`
  - chaser cue row: `time / chaser / calculated duration`
- Chaser row duration is calculated in the frontend from chaser beat offsets plus current song/playback BPM.
- Cue sheet preview dispatch is type-aware:
  - effect rows use `fixture.preview_effect`
  - chaser rows use `chaser.preview`
- Cue sheet edit dispatch is type-aware:
  - effect rows hydrate `EffectPicker`
  - chaser rows hydrate `ChaserPicker`

### DMX control
- `src/features/dmx_control/DmxControlView.ts`: fixture VM selection + grid rendering + partial value updates.
- `src/features/dmx_control/adapters/fixture_vm.ts`: backend `FixtureState` -> frontend `FixtureVM`, including `supported_effects` metadata normalization for the tray UI.
- `src/features/dmx_control/fixture_selectors.ts`: fixture selection entrypoint.
- `src/features/dmx_control/fixture_intents.ts`: DMX + preview + POI intent senders.
- `src/features/dmx_control/components/FixtureGrid.ts`: card grid and incremental control updates.
- `src/features/dmx_control/components/FixtureCard.ts`: fixture container with ARM action.
- `src/features/dmx_control/components/EffectTray.ts`: LoFi-style effect preview footer (`effect`, `duration`, dynamic params, `preview`).
- `src/features/dmx_control/components/controls/StandardControls.ts`: meta-channel-driven sliders/dropdowns.
- `src/features/dmx_control/components/controls/EnumGrid.ts`: slot-style enum control grid used for mapped wheels (color/gobo).
- `src/features/dmx_control/components/controls/RgbControls.ts`: color control + standard controls composition.
- `src/shared/components/controls/ColorPicker.ts`: shared color input control used by helper forms and DMX RGB controls.
- `src/features/dmx_control/components/controls/MovingHeadControls.ts`: pan/tilt surface + POI controller + standard controls.
- `src/features/dmx_control/components/controls/PanTiltControl.ts`: XY pad with throttled updates and commit callback.
- `src/features/dmx_control/components/controls/PoiLocationController.ts`: POI selector and `set` target action.
- `src/features/dmx_control/components/controls/UnknownControls.ts`: fallback channel sliders.
- `src/features/dmx_control/components/controls/*_helpers.ts`: shared helpers for pan/tilt math/drag and POI state logic.

### LLM chat
- `src/features/llm_chat/LlmChatView.ts`: chat card composition.
- `src/features/llm_chat/llm_state.ts`: status/messages/streaming reducer.
- `src/features/llm_chat/llm_intents.ts`: prompt/cancel intents and optimistic user message append.
- `src/features/llm_chat/components/*`: chat message, history, input controls.

### Layout/feedback/control primitives
- `src/shared/components/layout/*`: `Sidebar`, `RightPanel`, `Card`.
- `src/shared/components/feedback/*`: `StatusCard`, `Badge`, theme model.
- `src/shared/components/controls/*`: generic button/input/dropdown/slider/toggle/color-picker controls.
- `src/shared/utils/*`: id generation, throttling, time formatting, SVG icon creation.
- `src/shared/svg_icons/index.ts`: generated icon registry used by sidebar and transport controls.

## Styling and token contract

- `src/app/themes.css`: global design tokens and theme variants (`dark`, `tokyo-dark`, `light`).
- `src/app/AppShell.css`: shell columns (`sidebar | main | right-panel`) and main viewport behavior.
- `src/shared/components/layout/Sidebar.css`, `RightPanel.css`: persistent shell side areas.
- `src/shared/components/controls/Slider.css`: range slider skin.
- `src/shared/components/chords_panel/ChordsPanel.css`: shared chord progression panel styling.
- `src/shared/components/song_player/ui/SongPlayer.css`: player layout and transport styling.
- `src/features/dmx_control/DmxControl.css`: fixture cards, pan/tilt surface, POI controls.
- `src/features/llm_chat/LlmChat.css`: chat layout and message styles.

Use CSS variables from `themes.css` for visual values. Do not hardcode mockup colors/dimensions.

Frontend UI implementation rules:
- Use shared controls from `src/shared/components/controls` before creating primitive HTML form elements.
- Avoid redundant wrapper elements; add containers only when they are needed for layout, accessibility, or behavior.
- Put each panel in a dedicated folder named after that panel, and keep panel-local helpers/state in that folder instead of the feature root.
- When a panel or component is used by multiple pages, promote it to a shared component and place it in the appropriate shared folder rather than duplicating page-local copies.
- Keep CSS close to the owning feature or component. Do not use `src/app/themes.css` for feature-specific UI changes.
- Display song-position and cue-time values in `s.mmm` format consistently across views and controls.

## DMX LoFi layout contract

Reference: `docs/ui/LoFi mockups/4 DMX Control.png`.

- Moving-head card body uses a two-column split:
  - left: pan/tilt surface + POI selector/set action
  - right: mapped wheels + range sliders
- Right-column control order is deterministic:
  - wheels first (`enum`, and `u8` channels with `mapping` + `step=true`)
  - sliders second (`u8/u16`, including `u8+mapping` where `step` is not true)
- Mapped enum controls render as slot-style square grids, not native selects.
- `u8 + mapping` rendering matrix:
  - `step=true` => swatch/slot grid (sends mapped numeric key)
  - `step!=true` => slider (`step=1`, mapping used as cue only)
- Effect footer uses the LoFi structure: effect selector, duration input, params row, preview action.
- POI selection behavior in moving-head spatial:
  - selected POI with fixture target => move to target and hide `set`
  - selected POI without fixture target => move to `0,0` and show `set`
  - pan/tilt divergence from selected target => show `set`
- Pink annotation text in the mockup is guidance only and is not rendered in UI.

### DMX control handoff notes (for LLMs)

- Use the shared two-column layout class for fixture control bodies:
  - `fixture-two-col`
  - `fixture-two-col-left`
  - `fixture-two-col-right`
- Do not introduce new per-fixture two-column wrappers unless behavior requires a different layout model.
- Shared width contract:
  - Base layout reads `--fixture-left-column-width`.
  - Fixture-specific defaults are exposed on `.fixture-card`:
    - `--fixture-left-column-width-rgb`
    - `--fixture-left-column-width-moving-head`
  - Controls set `--fixture-left-column-width` from one of those defaults.
- Responsive contract:
  - At mobile breakpoint (`max-width: 1100px`), `.fixture-two-col` collapses to one column.
- RGB control contract:
  - `RgbPreview` uses native `<input type="color">` (`rgb-preview-input`).
  - Emit color updates on both `input` (continuous) and `change` events.
  - Preview label shows lowercase `#rrggbb`.
  - `RgbControls` sends semantic RGB updates via `fixture.set_values` payload key `values.rgb`.
  - Color grid and color input both send semantic HEX (not direct `red/green/blue` channel payloads).
- Backend/state expectation used by frontend:
  - RGB fixtures are read from `values.rgb` as canonical `#RRGGBB`.
  - Color-name mapping is frontend-local display logic; backend does not need to emit color names for RGB meta-channel values.

## Current implementation status

- `SongAnalysis` renders Song Loader plus the shared chord progression panel in the first column, Song Events plus the inert Event Tools placeholder in the second column, chord-pattern mining cards in the third column, and analysis plots in the fourth column when available.
- `ShowBuilder` reuses the shared chord progression card and renders a live mixed cue sheet plus builder tools for effects, chasers, and cue helpers.
- `ShowControl` renders a live sections panel backed by websocket song metadata, but its cue summary and fixture-effects panels are still static placeholder content.
- `HomeView` exists in source but is not part of current route rendering.

## Development commands

From `frontend/`:

```bash
deno task dev
```

```bash
deno task serve
```

```bash
deno task check
```

```bash
npm run sync-icons
```

## Frontend UI implementation rules

- Prefer flexbox for small/local component layout.
- Use grid only when the layout is truly two-dimensional and cannot be expressed cleanly with flexbox.
- Treat LoFi mockups as layout references only.
- Use existing token variables from `themes.css`.
- Keep backend integration capability-driven and backend-agnostic. Avoid frontend assumptions tied to one backend implementation.
- Prefer referencing explicit files from [../docs/ui/README.md](../docs/ui/README.md) instead of generic "mockup" wording in prompts.
- Never render instructional/mockup annotation text in the final UI.
- Never create UI labels directly from annotation callouts in LoFi files.
- Never copy annotation colors (including pink guidance text color) into production UI styles.
- Never ship annotation text or annotation color tokens into final HTML, DOM content, or production CSS.
- In `src/features`, use shared themed controls (`Button`, `Dropdown`, `Slider`, `Toggle`) instead of raw `button`, `select`, `input[type=range]`, or `input[type=checkbox]` elements.
- Do not create feature-local custom variants of those controls; extend shared control components when customization is required.

## Explicit coding style directives

- Use CUBE CSS; do not use BEM class patterns (`__`, `--`).
- CUBE model in this repo: Composition uses `l-`/`o-`, Utilities use `u-`, Blocks use semantic component names, Exceptions use `is-`/`has-`.
- Keep component structure as plain as possible; avoid wrapper-over-wrapper nesting unless required for semantics, accessibility, or behavior.
- Do not add padding or gap values unless explicitly required by the task or LoFi constraints.
- Keep feature CSS focused on layout and spacing. Do not style shared control internals from feature files (`.btn`, `.btn-content`, `.input-shell`, `.input-field`, `.dropdown`, `.toggle`, `.slider-row`).
- Keep control state visuals centralized in shared styles. Use shared state classes (`.is-active`, `.is-selected`) from `src/app/themes.css`.
- Do not add feature-scoped state variants such as `.selected`, `.is-current`, or feature-specific `.is-active` color/border overrides.
- For list rows with metadata + actions (such as show-builder playlist rows), use a two-column flex layout: left content block and right action block aligned to end.
- When adding or changing interactive UI behavior, wire state class toggling in TypeScript and rely on shared CSS tokens/styles for rendering.

## LLM UI task template

```text
Build/update <screen/component> to match the LoFi layout reference.

Layout constraints (authoritative):
- Keep placement/order exactly as in LoFi (columns, panel order, key section positions).
- Treat LoFi as layout-only reference; do not reinterpret structure.
- Never render annotation/instruction text from the mockup in the final UI.

Implementation constraints:
- Prefer flexbox for small/local component layout; use grid only for true two-dimensional layouts.
- Do not copy explicit mockup dimensions or colors.
- Use responsive sizing and project theme tokens/variables.
- In `src/features`, use shared themed controls (`Button`, `Dropdown`, `Slider`, `Toggle`) for interaction elements instead of bare HTML control tags.

Acceptance checks:
- Column/panel placement matches LoFi.
- Mobile and desktop both preserve intended structure.
- No hard-coded mockup colors/dimensions were introduced.
```
