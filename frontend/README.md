# Frontend Module (LLM Guide)

Preact + Vite authoring and playback UI for AI Light Show.

## Purpose

- Provide show control UI (timeline, fixtures, cues, preview).
- Keep audio timeline authoritative.
- Send/receive real-time WebSocket messages to/from backend.

## Primary entrypoints

- `src/App.jsx`: app root, router, shell composition.
- `src/app/state.jsx`: global app state + WebSocket client.
- `src/layout/AppShell.jsx`: persistent shell layout.
- `src/layout/RightPanel.jsx`: always-visible player/chat panel.
- `src/pages/*`: routed work areas (`/show`, `/analysis`, `/dmx`, `/builder`).

## State and networking model

- `AppStateProvider` opens one WebSocket to backend (`/ws`).
- On `initial`, frontend hydrates fixtures, cues, song, and status.
- During playback, frontend sends `timecode` and playback toggles.
- While paused, frontend can send `delta` edits and `preview_effect` requests.
- Frontend applies authoritative `dmx_frame` snapshots when paused/seeked.

## Important behavior constraints

- Audio timeline is source-of-truth for playback position.
- Frontend must not send effective editing actions while backend is playing.
- Preview requests should include a `request_id` for lifecycle tracking.

## Scripts

```bash
cd frontend
npm install
npm run dev
npm run build
npm run test:e2e
```

## Environment and endpoints

- Dev server default: `http://localhost:5173`
- WebSocket target from `VITE_WS_URL`; fallback is `${window.location.origin}/ws` (protocol-adjusted).

## Cross-module contract notes

- WebSocket payload shapes are defined by backend `api/websocket.py` behavior.
- Effect preview forms/options must match backend fixture effect contracts.

## LLM contributor checklist

1. Keep state updates idempotent across repeated WS events.
2. Avoid introducing backend assumptions not present in message payloads.
3. If adding/changing effects, update `src/components/dmx/effectPreviewConfig.js` with backend changes.
4. Validate against both paused authoring and active playback flows.
