# AI Light Show — UI

This doc describes the *current* frontend implementation.

## App shell (persistent)

- Left menu: icon-only navigation.
- Routes/pages:
  - `/show` — Show Control
  - `/analysis` — Song Analysis
  - `/dmx` — DMX Controller
  - `/builder` — Show Builder (placeholder)
  - `/` redirects to `/show`
- Right panel (persistent):
  - Show Player (always visible)
  - LLM Chat (always visible)

## Show Control (/show)

- Waveform header (WaveSurfer): displays waveform + title.
- Playback:
  - The *only* play/pause control is in the right-panel Show Player.
  - Waveform header has no play/pause or load-song buttons.
- Lanes (main column):
  - Song parts lane (from metadata when available)
  - Cue sheet lane
  - Fixtures lane (DMX sliders + effect preview controls)

Show control behavior:

- While playback is active, fixture editing and preview actions are disabled.
- While paused, fixture edits apply immediately and can be captured into cues.
- Preview button runs a temporary backend effect preview (non-persistent).

## Song Analysis (/analysis)

- Shows the currently loaded song.
- Includes `Start analysis` action (sends `analyze_song` message).
- Displays task status, progress bar, current step/status metadata, and error text.

## DMX Controller (/dmx)

- Fixture-first card UI:
  - Moving head cards: XY pad, wheel selections, presets, channel sliders.
  - RGB/parcan cards: color presets and channel sliders.
  - Generic card fallback for unknown fixture types.
- Each fixture card includes effect preview controls at the bottom:
  - Effect dropdown (filtered to backend-supported effects)
  - Duration input (seconds)
  - Dynamic parameter inputs (from `effectPreviewConfig.js`)
  - `Preview` button to execute immediately

Preview behavior:

- Preview is disabled while playback is active.
- Preview does not mutate stored cue sheets.
- Preview does not animate/overwrite editor slider values in the UI.

## Show Builder (/builder)

- Current: placeholder page.
