# DMX Control UI Implementation Guide (LLM-Friendly)

This guide defines exactly how to implement the `/dmx` page shown in `docs/ui/LoFi DMX Control.png`.

Scope:
- Implement the DMX Control frontend UI and interactions.
- Use existing WebSocket/app-state wiring.
- Ignore pan/tilt constraints for now.

Out of scope:
- Backend protocol changes.
- New message types.
- Fine visual polish beyond Lo-Fi parity.

---

## 1. Implementation Goals

Build a fixture-centric control page with:
- Moving-head cards:
  - Arm button
  - XY pad for pan/tilt
  - POI preset buttons
  - Color wheel buttons
  - Gobo wheel buttons
  - Sliders for prism, strobe, dimmer
- RGB par-can cards:
  - Arm button
  - Color preset swatches
  - Sliders for red, green, blue, strobe, dimmer
- Existing right panel (chat + player) remains unchanged.

---

## 2. Existing Project Facts (Do Not Rebuild)

- Router and page:
  - `frontend/src/App.jsx` already routes `/dmx` to `DmxControllerPage`.
- Shared app state and DMX write action:
  - `frontend/src/app/state.jsx`
  - Use `actions.handleDmxChange(channel, value)` for all DMX outputs.
- Right panel is already persistent and wired:
  - `frontend/src/layout/RightPanel.jsx`
  - `frontend/src/components/chat/ChatSidePanel.jsx`
  - `frontend/src/components/player/PlayerPanel.jsx`
- Fixtures arrive via WebSocket `initial` payload and include:
  - `fixture.type`
  - `fixture.channels`
  - `fixture.arm`
  - `fixture.presets`
  - `fixture.meta.value_mappings`

---

## 3. Required File Changes

Implement with this structure:

1. Update page:
- `frontend/src/pages/DmxControllerPage.jsx`

2. Add components:
- `frontend/src/components/dmx/DmxFixtureGrid.jsx`
- `frontend/src/components/dmx/MovingHeadCard.jsx`
- `frontend/src/components/dmx/RgbParCard.jsx`
- `frontend/src/components/dmx/XYPad.jsx`
- `frontend/src/components/dmx/ChannelSlider.jsx`
- `frontend/src/components/dmx/WheelButtonRow.jsx`
- `frontend/src/components/ui/CustomRangeSlider.jsx`

3. Add helpers:
- `frontend/src/components/dmx/dmxUtils.js`

4. Add styles:
- `frontend/src/index.css` (append DMX-specific section)

---

## 4. Data/Behavior Contracts

### 4.1 DMX value rules

- DMX channel values are `0..255`.
- Coerce outgoing values:
  - `Number(value)`
  - `Math.round`
  - clamp to `[0, 255]`

### 4.2 16-bit pan/tilt rules (ignore constraints)

For moving heads:
- Treat pan and tilt as unconstrained 16-bit values: `0..65535`.
- `pan_msb` + `pan_lsb` compose pan.
- `tilt_msb` + `tilt_lsb` compose tilt.

Helpers:
- Compose:
  - `value16 = (msb << 8) | lsb`
- Split:
  - `msb = (value16 >> 8) & 255`
  - `lsb = value16 & 255`

XY mapping:
- x in `[0, 1]` maps to pan16 in `[0, 65535]`.
- y in `[0, 1]` maps to tilt16 in `[0, 65535]`.
- Invert y if needed so top feels like lower tilt value; pick one and keep consistent.

### 4.3 Arm button behavior

When `Arm` is clicked:
- Read `fixture.arm`, expected shape: `{ channelName: value }`
- For each entry:
  - resolve channel number from `fixture.channels[channelName]`
  - send via `actions.handleDmxChange(channelNum, value)`

### 4.4 POI button behavior (moving head)

For each preset in `fixture.presets`:
- Render button with `preset.name`.
- On click, apply every key/value in `preset.values`.
- Each key is a channel name (example: `pan_msb`).
- Resolve to channel number via `fixture.channels[key]`.
- Send each channel write via `actions.handleDmxChange`.

### 4.5 Wheel mapping behavior

For moving head `color` and `gobo`:
- Use `fixture.meta.value_mappings.<wheelName>` if present.
- This is a map of DMX values to labels.
- Render selectable buttons in numeric DMX order.
- On select, write mapped DMX value to the relevant channel.

---

## 5. Component Specs

### 5.1 `DmxControllerPage.jsx`

Responsibilities:
- Pull `fixtures`, `dmxValues`, `actions` from `useAppState()`.
- Render a page wrapper + header.
- Render `DmxFixtureGrid` with those props.
- Remove placeholder card text.

### 5.2 `DmxFixtureGrid.jsx`

Props:
- `fixtures`
- `dmxValues`
- `onDmxChange`

Behavior:
- Empty state if no fixtures.
- Render cards by type:
  - `moving_head` -> `MovingHeadCard`
  - `rgb` -> `RgbParCard`
  - fallback generic card (name + channel sliders)

### 5.3 `MovingHeadCard.jsx`

Props:
- `fixture`
- `dmxValues`
- `onDmxChange`

Render sections:
- Header: fixture name + `Arm` button.
- Left block: `XYPad` and POI buttons.
- Right block:
  - `WheelButtonRow` for `color`
  - `WheelButtonRow` for `gobo`
  - `ChannelSlider` rows for `prism`, `strobe`, `dim` (if channel exists)

### 5.4 `RgbParCard.jsx`

Props:
- `fixture`
- `dmxValues`
- `onDmxChange`

Render sections:
- Header: fixture name + `Arm` button.
- Color preset swatch grid:
  - Use fixed presets: white/red/green/blue/cyan/magenta/yellow/off.
  - Each swatch applies combined RGB channel writes.
- Sliders:
  - `red`, `green`, `blue`, `strobe`, `dim` (only if channel exists)

### 5.5 `XYPad.jsx`

Props:
- `pan16` (current composed value)
- `tilt16` (current composed value)
- `onChange(pan16, tilt16)`

Behavior:
- Click and drag updates both values continuously.
- Pointer events:
  - `pointerdown`: capture pointer + update
  - `pointermove`: update if dragging
  - `pointerup`/`pointercancel`: stop dragging
- Crosshair and current-point marker should be visible.

### 5.6 `ChannelSlider.jsx`

Props:
- `label`
- `value` (0..255)
- `onInput(nextValue)`
- optional `min`/`max` default to `0/255`

Behavior:
- Horizontal range input + value display.
- Internally use `CustomRangeSlider` to keep consistent styling.

### 5.8 `CustomRangeSlider.jsx`

Use the concept from:
- https://codingartistweb.com/2021/07/custom-range-slider-html-css-javascript/

Requirements:
- Build our own component and styles (do not copy/paste template code).
- Track should show two-tone fill:
  - active/fill color from min to current value
  - muted track color from current value to max
- Thumb should be a circular blue handle.
- Current numeric value should be shown in a compact badge at the right side.
- Expose props:
  - `min`, `max`, `step`, `value`, `onInput`, `ariaLabel`, `showValue`
- Compatible with DMX values (`0..255`) and reusable for future controls.

### 5.7 `WheelButtonRow.jsx`

Props:
- `label`
- `channelNum`
- `valueMappings` (object map)
- `currentValue`
- `onSelect(value)`

Behavior:
- Render button list from mapping entries sorted numerically by DMX value.
- Highlight selected button.

---

## 6. Utility Functions (`dmxUtils.js`)

Implement at least:

- `clampByte(value)` -> `0..255`
- `readChannel(dmxValues, channelNum)` -> byte with default `0`
- `writeChannel(onDmxChange, channelNum, value)` -> clamped write
- `compose16(msb, lsb)` -> `0..65535`
- `split16(value16)` -> `{ msb, lsb }`
- `write16(onDmxChange, msbChannel, lsbChannel, value16)`
- `getWheelOptions(fixture, wheelName)`:
  - read `fixture.meta?.value_mappings?.[wheelName]`
  - return sorted array like `{ value, label }[]`

---

## 7. Styling Requirements (`index.css`)

Add a DMX section with classes for:
- `.dmxPage`
- `.dmxHeader`
- `.dmxGrid`
- `.dmxCard`
- `.dmxCardHeader`
- `.dmxCardBody`
- `.movingHeadLayout`
- `.xyPad`
- `.xyPadCrosshair`
- `.xyPadMarker`
- `.poiGrid`
- `.wheelRow`
- `.wheelButton`
- `.wheelButtonActive`
- `.sliderRow`
- `.rgbPresetGrid`
- `.rgbPresetButton`

Layout behavior:
- Desktop: 2 columns in center area.
- Small screens: 1 column.
- Keep Lo-Fi grayscale look and 1px borders.

---

## 8. Step-by-Step Build Order

1. Create `dmxUtils.js`.
2. Build `ChannelSlider.jsx` and `WheelButtonRow.jsx`.
3. Build `CustomRangeSlider.jsx` + CSS styles.
4. Build `XYPad.jsx` (pointer drag + marker).
5. Build `MovingHeadCard.jsx` using helpers/components.
6. Build `RgbParCard.jsx`.
7. Build `DmxFixtureGrid.jsx`.
8. Replace placeholder in `DmxControllerPage.jsx`.
9. Add DMX CSS classes to `index.css`.
10. Run build and verify no lint/syntax errors.

---

## 9. Acceptance Criteria

Functional:
- `/dmx` shows fixture cards instead of placeholder.
- Moving head XY drag updates pan/tilt by writing both MSB+LSB channels.
- Arm button writes all `fixture.arm` channel values.
- POI preset buttons apply preset channel writes.
- Wheel buttons set the mapped DMX value for selected slot.
- RGB fixtures provide color preset buttons and RGB/strobe/dimmer sliders.
- All controls use `actions.handleDmxChange`.

Visual:
- Page structure follows Lo-Fi mockup: fixture cards left/center and persistent right panel.
- Controls are dense, bordered, grayscale, and readable.

Robustness:
- Missing optional channels do not crash; hide that control row.
- Empty fixtures array shows a simple empty state message.

---

## 10. Manual Test Script

1. Open `/dmx`.
2. Confirm moving head card appears.
3. Drag XY pad and verify pan/tilt channels change in backend/logs.
4. Click each POI and verify multiple channel writes occur.
5. Click Arm and verify arm channels are written.
6. Click color and gobo wheel slots and confirm selected state/value changes.
7. On RGB fixture, move RGB/strobe/dim sliders and click color presets.
8. Confirm right chat/player remain visible and functional.

---

## 11. Notes for Future Iteration

- Re-introduce `meta.position_constraints` once calibration UX is decided.
- Add arm/disarm toggle state when backend supports explicit disarm semantics.
- Consider extracting fixture-control schema so control rows are declarative per fixture type.
