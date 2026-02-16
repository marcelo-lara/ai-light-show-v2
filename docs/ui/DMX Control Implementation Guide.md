# DMX Control UI — Current Implementation Reference

This document describes the current `/dmx` implementation and integration points.

## Scope

Implemented in the frontend:

- Fixture-first DMX control cards.
- Moving-head XY pan/tilt control (16-bit split writes).
- Wheel mapping buttons (color/gobo) where available.
- Fixture presets/arm actions.
- Per-fixture effect preview controls (dropdown + duration + parameter inputs + Preview button).

## Main files

- `frontend/src/pages/DmxControllerPage.jsx`
- `frontend/src/components/dmx/DmxFixtureGrid.jsx`
- `frontend/src/components/dmx/MovingHeadCard.jsx`
- `frontend/src/components/dmx/RgbParCard.jsx`
- `frontend/src/components/dmx/EffectPreviewControls.jsx`
- `frontend/src/components/dmx/effectPreviewConfig.js`
- `frontend/src/components/dmx/dmxUtils.js`
- `frontend/src/components/ui/CustomRangeSlider.jsx`
- `frontend/src/index.css`

## Runtime behavior

### Edit behavior

- All DMX writes use `actions.handleDmxChange(channel, value)`.
- While playback is active, frontend controls are disabled and backend rejects live deltas (`delta_rejected`).
- While paused, manual edits can drive output directly.

### Preview behavior

- Preview is triggered via WebSocket message `preview_effect`.
- Backend validates and runs a temporary in-memory preview canvas.
- Preview is non-persistent (not stored in cues/files).
- If playback starts, preview is canceled immediately.

### UI preview controls per fixture

- Effect dropdown: options filtered by fixture type + backend-supported effects.
- Duration input: float seconds.
- Dynamic parameter inputs: sourced from `effectPreviewConfig.js`.
- Preview button: sends `{ fixture_id, effect, duration, data }` through app state.

## Data contracts

### Fixture metadata consumed by UI

- `fixture.type`
- `fixture.channels`
- `fixture.arm`
- `fixture.presets`
- `fixture.effects`
- `fixture.meta.value_mappings`

### 16-bit pan/tilt (moving heads)

- Compose: `(msb << 8) | lsb`
- Split: `msb = (value >> 8) & 255`, `lsb = value & 255`
- Value range: `0..65535`

## Synchronization rule (mandatory)

Whenever backend fixture effects are added, removed, renamed, or parameter contracts change, update:

- `frontend/src/components/dmx/effectPreviewConfig.js`

in the same change so preview effect options and dynamic form inputs stay aligned with backend runtime support.

## Related docs

- `docs/ui/UI.md`
- `docs/architecture/frontend.md`
- `docs/architecture/backend.md`
