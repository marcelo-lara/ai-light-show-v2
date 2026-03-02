# UIX Frontend Implementation Instructions (for VSCode Copilot GPT-5.2)

## Goal
Build a UIX-based frontend from scratch that connects to an existing Python backend (FastAPI) using **WebSockets** for near real-time interaction. The frontend must be a "dumb console": it renders authoritative backend state and sends user intents. All domain logic lives in the backend.

## Non-negotiable rules
1. **Backend is authoritative.**
   - The frontend MUST NOT compute domain state (e.g., MUST NOT derive `show_state` from playback).
   - The UI only displays backend-provided state and emits intents.
2. **WebSocket-only** for control and realtime state sync.
   - Do not add REST calls for state (except optional static assets).
3. **Hydration-aware UI.**
   - Render shell immediately; apply bootstrap state if available; mark state stale until WS snapshot arrives.
4. **Patch-based updates.**
   - Backend sends snapshot + patches. UI must apply patches deterministically with sequence checks.

---

## High-level UI layout
The application has 4 main screens:
- Home
- Song Analysis
- Show Builder
- DMX Control

The UI has a persistent layout:
- Left: Sidebar navigation
- Center: Main screen content
- Right: Right panel with:
  1) **Status Card** (top, always visible)
  2) **LLM Chat Card** (below, streaming + state display)

Status Card must show:
- WS: Connecting / Connected / Reconnecting / Disconnected
- Show: Running / Idle (FROM BACKEND FIELD ONLY)
- Playback: Playing / Paused / Stopped + timecode
- Edits lock: Locked/Unlocked (FROM BACKEND)
- ARM summary: armed_count / total_fixtures (FROM BACKEND or derived from backend fixture list only)
- LLM: Idle / Streaming / Error (from chat subsystem)

---

## Project structure (feature-based)
Implement this structure:

src/
  app/
    main.ts
    AppShell.ts
    routes.ts
    boot.ts

  shared/
    transport/
      ws_client.ts
      protocol.ts
      protocol_validate.ts        # optional runtime validation
    state/
      backend_state.ts
      ui_state.ts
      selectors.ts
    components/
      layout/
        Sidebar.ts
        RightPanel.ts
        Card.ts                   # basic card container
      feedback/
        StatusCard.ts
        Badge.ts
      controls/
        Slider.ts
        Toggle.ts
        Knob.ts                   # optional
        Dropdown.ts
        ColorSwatch.ts
      utils/
        throttle.ts
        format.ts                 # timecode, labels, etc.

  features/
    home/
      HomeView.ts
    song_analysis/
      SongAnalysisView.ts
      components/
        AnalysisPlot.ts
        BeatTable.ts
        ChordsPanel.ts
    show_builder/
      ShowBuilderView.ts
      components/
        SongProgression.ts
        EffectPlaylist.ts
        EffectPicker.ts
    dmx_control/
      DmxControlView.ts
      fixture_intents.ts
      fixture_selectors.ts
      adapters/
        fixture_vm.ts
      components/
        FixtureGrid.ts
        FixtureCard.ts
        EffectTray.ts
        controls/
          MovingHeadControls.ts
          RgbControls.ts
          UnknownControls.ts
    llm_chat/
      LlmChatView.ts
      llm_state.ts
      llm_intents.ts
      components/
        ChatHistory.ts
        ChatMessage.ts
        PromptInput.ts

---

## WebSocket protocol requirements

### Connection lifecycle
- On connect, UI sends `{type:"hello", client:"uix-ui", version:"0.1"}` (if backend supports; otherwise ignore).
- Backend responds with a full `snapshot`.
- After that, backend sends `patch` messages at a steady cadence (e.g., 30Hz) or event-driven.

### Message types (frontend expects)

Inbound from backend:
- snapshot:
  - full state payload + `seq`
- patch:
  - `seq` + list of changes `{path: [...], value: any}`
- event:
  - notifications/warnings/errors

Outbound from UI:
- intents only (examples):
  - play/pause/stop
  - jump_to_time / jump_to_section / jump_to_beat
  - set_arm
  - set_fixture_values
  - preview_effect
  - stop_preview (optional)
  - llm_send_prompt (if LLM is routed through backend WS)

### Sequence ordering
- UI must track last applied `seq`.
- Ignore patches with `seq <= last_seq`.

---

## Hydration strategy
Implement a boot flow that supports:
1) SSR shell (if UIX server renders) OR immediate shell (client-only)
2) Bootstrap state
3) WS snapshot replaces bootstrap state

Implementation details:
- In `boot.ts`, initialize stores:
  - `backend_state.init(bootstrapSnapshot, {stale:true})` if available
  - `ui_state.init(...)`
- Then connect WS and wait for snapshot:
  - on snapshot: `backend_state.applySnapshot(snapshot)` sets stale=false
- If only cached bootstrap exists, show StatusCard "Stale" until snapshot arrives.

Bootstrap sources (use in this order):
1) `window.__BOOTSTRAP_STATE__` (injected JSON object if available)
2) `localStorage.getItem("last_snapshot")` (optional)
3) none → start empty, stale=true

Persist:
- last valid snapshot to localStorage (optional)
- UI preferences: selected fixture, last route (optional)

---

## Authoritative system fields (do not derive)
### MUST be provided by backend and displayed verbatim
- `system.show_state` must be `"running"` or `"idle"` (later may expand)
- `system.edit_lock` must be boolean or enum `"locked"|"unlocked"`
- `playback.state` must be `"playing"|"paused"|"stopped"`

### Frontend MUST NOT do:
- `show_state = playback.state === "playing" ? "running" : "idle"`
- Any similar domain inference.

If backend does not provide `system.show_state`, display "Unknown" and file a backend task.

---

## Status Card implementation
`shared/components/feedback/StatusCard.ts` must:
- Read WS connection state from WS client
- Read authoritative backend state from `backend_state`
- Read LLM stream state from `llm_chat/llm_state`

Show at least:
- WS badge
- Show badge: Running/Idle/Unknown (from backend)
- Playback badge: Playing/Paused/Stopped + timecode
- Edits badge: Locked/Unlocked
- ARM badge: count armed fixtures (allowed: count `fixtures[*].armed`)
- LLM badge: Idle/Streaming/Error

---

## DMX Control page (composition over inheritance)

### FixtureCard pattern
Implement `FixtureCard` as a shared container:
- Header: fixture name + type + ARM toggle + status indicators
- Body slot: specialized controls renderer (MovingHeadControls or RgbControls)
- Footer: shared `EffectTray` with common actions

### Specialized controls
- MovingHeadControls: pan/tilt pad, wheels, prism if present, dimmer/strobe, etc.
- RgbControls: RGB sliders, color presets, dimmer/strobe
- UnknownControls: shows raw channels as fallback sliders

### Capability-driven rendering
Do not hardcode features. Prefer backend-provided capabilities; otherwise map by fixture type for now.

### ARM concept (reference)
ARM is a backend feature: a set of channels that must be forced to values to allow light output.
Example:
- shutter channel must be open (ch7=255) before dimmer works (ch6=200).
Frontend only toggles `armed` state and displays it. Mask logic remains in backend.

---

## Input throttling rules (real-time)
Sliders and XY pad must be throttled:
- During pointer drag: send at most one intent per 16ms (or 33ms)
- On pointer up: always send final value
Use `shared/utils/throttle.ts` with consistent behavior across controls.

---

## LLM Chat panel
LLM chat is a streaming UI:
- Show message list
- Show streaming state while receiving tokens
- Can reference state, but does not own it
Implement:
- `llm_state.ts` store
- `llm_intents.ts` sends prompt via backend WS intents

Place StatusCard above Chat Card in RightPanel.

---

## Acceptance tests (manual)
1) App loads: sidebar + right panel visible immediately; StatusCard shows "Connecting…" then "Connected".
2) If bootstrap snapshot exists: UI renders instantly and shows "Stale" until WS snapshot arrives.
3) `system.show_state="running"` shows "Show: Running" regardless of playback state.
4) DMX Control:
   - ARM toggle sends intent; backend echoes state.
   - Slider drag is throttled.
5) LLM chat:
   - Send prompt shows streaming indicator; updates as stream arrives.

---

## Implementation order
1) AppShell + Sidebar + RightPanel + StatusCard + routing
2) WS client + backend_state snapshot/patch + hydration boot
3) DMX Control MVP: FixtureGrid + FixtureCard + RgbControls + EffectTray
4) Add MovingHeadControls + capabilities adapter
5) Home transport intents
6) LLM Chat streaming UI
7) Song Analysis / Show Builder (read-only → editable)


---

## Theme system (user-selectable)
A basic theme system is included.

Files:
- `src/app/themes.css` (CSS variable token sets for `dark`, `tokyo-dark`, `light`)
- `src/shared/state/theme_state.ts` (init/apply + localStorage persistence)
- `src/shared/components/feedback/ThemeSelector.ts` (logic model for a dropdown)

Rules:
- Call `initTheme()` **before** mounting UI (already done in `src/app/boot.ts`) to avoid flashes.
- Components should use CSS variables (tokens) rather than hard-coded colors.
- Add a small theme selector control inside the Status Card (recommended).
