# AI Light Show — UI

This doc describes the *current* frontend implementation.

## App shell (persistent)

- Left menu: icon-only navigation.
- Routes/pages:
  - `/show` — Show Control
  - `/dmx` — DMX Controller (placeholder)
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
  - Fixtures lane (DMX sliders)

## DMX Controller (/dmx)

- Current: placeholder page.

## Show Builder (/builder)

- Current: placeholder page.
