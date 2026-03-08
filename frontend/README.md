# AI Light Show v2 — Frontend

The frontend is a UIX-based client for the AI Light Show system. It acts strictly as a "dumb console" that connects to the backend over WebSockets, renders authoritative state, and emits user intents.

## Core Principles

1. **Strictly a Client (No DMX Logic)**
   All DMX logic, state computations, and show rendering happen on the backend. The frontend MUST NOT compute or derive domain state natively.
2. **WebSocket-Only Control**
   The UI communicates with the backend via WebSockets (`/ws`), using a structured protocol of `hello`, `intent`, `snapshot`, `patch`, and `event`.
3. **Timecode Synchronization**
   The **ONLY** exception to backend authority is timecode sync. During playback, the frontend browser's audio timeline is authoritative. It sends regular `transport.jump_to_time` syncs so the backend follows the song position.
4. **Hydration-Aware Data**
   The application initializes a shell, applies bootstrap state (if available), and updates it seamlessly when the initial WebSocket snapshot arrives. Updates apply via sequence-ordered JSON patches.

## UI Layout & Structure

The interface has four main screens:
- **Home:** Session overview and general transport controls.
- **Song Analysis:** Visualizations of song metadata (beats, chords, sections).
- **Show Builder:** High-level song progression and effect sequencing.
- **DMX Control:** Hands-on hardware control tools (composed from modules like `FixtureCard`, `EffectTray`, etc.).

A persistent UI layout contains:
- A navigation **Sidebar** on the left.
- A central viewport for feature screens.
- A **Right Panel** with a always-visible **Status Card** displaying backend metrics (e.g. Connection, Playback Sync, Lock State) and an **LLM Chat Card** for interacting with the streaming AI tool.

## Technical Details

- **Framework:** UIX (via Deno).
- **Intent Throttling:** Direct device controls (e.g. RGB and Pan/Tilt sliders) actively throttle intent emissions during drag events and guarantee a final dispatch on pointer-up.
- **System Field Accuracy:** The UI strictly reflects explicit backend strings for core variables (like `show_state` running/idle), never assuming or mapping implicit logic.