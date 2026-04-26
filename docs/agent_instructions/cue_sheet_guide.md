# Cue Sheet Guide

This document is the technical reference for cue authoring. Use it for MCP workflow, cue JSON shape, fixture and effect contracts, POI and channel constraints, and render validation.

For palette, mood, section identity, and other creative direction, use [show_creation_guide.md](./show_creation_guide.md).

## Scope

This guide owns:

- backend cue tool workflow
- persisted cue sheet structure in `backend/cues/{song}.json`
- fixture IDs, spatial mapping, and capability differences
- effect payloads and technical channel values
- chaser timing mechanics
- helper invocation
- validation and common technical failure modes

This guide does not own artistic direction.

## Using The Backend Cue Tools

Use the backend cue MCP tools as the primary interface for cue work. The backend persists the resulting cue sheet to `backend/cues/{song}.json` automatically, so reason about the JSON schema but prefer MCP operations for edits, validation, and rendering.

Key tools:

- `cue.clear`: remove all cues within a specific time range before rebuilding that window
- `cue.propose`: submit a new set of cue rows for a section or phrase window
- `cue.apply_helper`: generate structured cue groups from helper logic such as `song_draft`
- `cue.render`: render the DMX canvas and produce validation output

Operational rule: always clear a time window before proposing replacement cues for that same window.

## Cue Sheet Structure

The cue sheet is a flat JSON array of cue entries. Each entry is either an effect row or a chaser row.

File location: `backend/cues/{song_id}.json`

For the full storage contract, validation rules, and examples, see [docs/architecture/backend_cues_schema.md](../architecture/backend_cues_schema.md).

### Effect Entry

```json
{
  "time": 1.234,
  "fixture_id": "id",
  "effect": "name",
  "duration": 0.5,
  "data": {},
  "name": "Optional",
  "created_by": "agent"
}
```

Required fields: `time`, `fixture_id`, `effect`, `duration`.

### Chaser Entry

```json
{
  "time": 10.5,
  "chaser_id": "id",
  "data": {
    "repetitions": 1
  },
  "created_by": "agent"
}
```

Required fields: `time`, `chaser_id`. Chaser rows remain persisted as chaser rows and expand only during preview or canvas rendering.

## Fixture Reference

Fixtures are grouped by capability.

| Type | Typical IDs | Capabilities |
| :--- | :--- | :--- |
| Prism Moving Heads | `mini_beam_prism_l`, `mini_beam_prism_r` | Pan/Tilt, Dimmer, Strobe, Color Wheel, Gobo Wheel, Prism |
| Center Moving Head | `head_el150` | Pan/Tilt, Dimmer, Shutter, Color Wheel, Gobo Wheel |
| Parcans | `parcan_l`, `parcan_r`, `parcan_pl`, `parcan_pr` | RGB Color Mix, Dimmer |

Spatial order from left to right:

- `parcan_pl`
- `mini_beam_prism_l`
- `parcan_l`
- `head_el150`
- `parcan_r`
- `mini_beam_prism_r`
- `parcan_pr`

Moving-head differences:

- `mini_beam_prism_l` and `mini_beam_prism_r` expose a prism channel and are the mirrored pair.
- `head_el150` has shutter control, no prism channel, and different wheel maps from the prism pair.

## POI Rules

Do not guess POIs. Read `backend/fixtures/pois.json` and only use POIs mapped for the target fixture.

Reference POI categories:

- named room POIs such as `piano`, `table`, `sofa`, `dark_desk`, `inblue_desk`, `wall`, and `ceiling_station`
- cardinal references such as `ref_0_0_0` through `ref_1_1_1`

Operational usage:

- use mapped room POIs for direct positioning targets
- use `ref_x_y_z` POIs for geometry-driven starts and ends in `sweep`, `orbit`, and similar motion effects
- `circle` should target a room POI with real location data rather than a reference cube point

## Effect Contracts

### Moving Head Effects

| Effect | Data Parameters | Notes |
| :--- | :--- | :--- |
| `move_to` | `pan`, `tilt` | Direct interpolation to explicit coordinates |
| `move_to_poi` | `target_POI` | Direct move to a mapped POI |
| `circle` | `target_POI`, `radius`, `orbits` | World-space circular motion around a POI |
| `orbit` | `subject_POI`, `start_POI`, `orbits`, `easing`, `write_dimmer` | Spiral toward the subject |
| `orbit_out` | `subject_POI`, `start_POI`, `orbits`, `easing`, `write_dimmer` | Spiral away from the subject |
| `sweep` | `start_POI`, `subject_POI`, `end_POI` | Arced motion with preroll |
| `strobe` | `rate` | Dimmer-based toggle |
| `full` | none | Immediate full intensity |
| `flash` | none | Decay from full intensity over `duration` |
| `fade_in` | `intensity` | Ramp from current state to target intensity |
| `fade_out` | `intensity` | Ramp toward blackout |
| `blackout` | none | Immediate blackout |

### Parcan Effects

| Effect | Data Parameters | Notes |
| :--- | :--- | :--- |
| `full` | `red`, `green`, `blue` | Immediate RGB set, default white when omitted |
| `flash` | `color`, `brightness` | Color hit that fades out |
| `fade_in` | `red`, `green`, `blue` | Smooth RGB transition |
| `strobe` | `rate` | Toggle between color and off |
| `blackout` | none | LEDs off |

### `set_channels`

Use `set_channels` for wheel color, gobo, prism, shutter, dim floor, and other non-positional channel values.

Mini Beam Prism example:

```json
{
  "time": 12.0,
  "fixture_id": "mini_beam_prism_l",
  "effect": "set_channels",
  "duration": 0.0,
  "data": {
    "channels": {
      "color": 55,
      "gobo": 58,
      "prism": 200
    }
  },
  "created_by": "agent"
}
```

Head EL-150 example:

```json
{
  "time": 12.0,
  "fixture_id": "head_el150",
  "effect": "set_channels",
  "duration": 0.0,
  "data": {
    "channels": {
      "color": 150,
      "gobo": 12,
      "shutter": 255
    }
  },
  "created_by": "agent"
}
```

#### Gobo Maps

`head_el150`:

- `0`: `Open`
- `12`: `Tunnel`
- `24`: `BigOval`
- `36`: `SmallOval`
- `48`: `Squares`
- `60`: `Shapes`
- `72`: `Tribal`
- `84`: `Slashes`

`mini_beam_prism_l` and `mini_beam_prism_r`:

- `0`: `Open`
- `8`: `Flower`
- `13`: `GuitarPluck`
- `18`: `Circles`
- `23`: `Square`
- `28`: `Radioactive`
- `33`: `Triangle`
- `38`: `Fan`
- `43`: `WiFi`
- `48`: `Xsess`
- `53`: `Asterisk`
- `58`: `Line`
- `63`: `Star`
- `68`: `RoundFlower`
- `73`: `Dot`

#### Useful Channel Values

Prism heads color wheel:

- `0`: Open/White
- `15`: Red
- `25`: Orange
- `35`: Yellow
- `45`: Green
- `55`: Blue
- `65`: Indigo
- `75`: Cyan
- `85`: Cool White
- `95`: Magenta

Prism channel:

- `0`: Off
- `130`: On
- `200`: Rotate

EL-150 color wheel:

- `0`: White
- `25`: Orange
- `50`: Cyan
- `75`: Purple
- `100`: Yellow
- `125`: Green
- `150`: Blue
- `175`: Red

EL-150 shutter operational rule: keep `shutter: 255` whenever the beam should be open.

## Chasers

Chasers are defined as one file per chaser under `backend/chasers/*.json`. They use beat-relative timing.

Current chasers:

- `blue_parcan_chase` — static, 4-beat blue pulse across all parcans
- `downbeats_and_beats` — static, beat-accent parcan hits
- `heartbeat` — static, slow pulse effect
- `drop-and-explode` — static, impact burst
- `parcan_blue_wave` — **dynamic** (`dynamic_wave_generator`), sine-modulated organic blue wave traveling left-to-right across all four parcans; params: `fixtures`, `base_color`, `accent_color`, `duration_beats`, `speed`, `step_size`, `fade_in_beats`, `fade_out_beats`

Timing mechanics:

- `effects[].beat` is an offset inside the pattern
- `effects[].duration` is also in beats
- total cycle length is the largest `beat + duration` in the chaser definition
- some chasers intentionally spill past beat 4, so compute the full inferred cycle before using them as bar-aligned motifs
- if a hard blackout or handoff is required, make sure no active chaser cycle extends past that cutoff

## Helpers

Helpers are invoked through `cue.apply_helper`.

- `song_draft`: generates a first-pass show from section timing, loudness, and accents
- `downbeats_and_beats`: applies a rhythmic pattern across a full song or bounded range using `fixture_ids`, `start_time`, and `end_time`

## Operational Authoring Rules

### Timing And Windowing

- align cue times to real beat or bar timestamps whenever possible
- use exact section or beat timestamps when rewriting a bounded window; do not round down below the window start
- clear the target time window before proposing replacement cues

### Conflict Avoidance

- use only valid fixture IDs and POIs
- do not stack duplicate `time + fixture_id + effect` rows unless the duplication is intentional and supported
- do not interrupt a moving-head travel phrase with another motion row before the fixture has time to land unless the replacement is deliberate

### Mechanical Timing

- prism fixtures need preroll
- assume about 2 seconds for a full pan travel and about 1 second for a full tilt travel on the prism pair
- if a visible hit depends on a prism arriving at a destination, author the move early enough for the render to settle before the hit

### Visible-Motion Validation

If `backend/cues/{song}.dmx.log` exists, treat it as an optional rendered-output check when motion readability or dimmer layering matters.

Validate these conditions:

- pan and tilt should change smoothly through the rendered window
- dimmer values should remain visible during motion when the intended design calls for readable travel
- midpoint color or dimmer changes should appear in rendered frames, not only in authored `set_channels` rows

Important failure mode:

- `orbit` or `sweep` can begin earlier than the authored cue time because of preroll
- if the motion effect writes dimmer and samples its initial dim before a later brightness-establishing row runs, the render can show a bright first frame followed by dark travel

Preferred fixes:

- set `write_dimmer: false` on the motion effect and author dimmer behavior explicitly
- or move the brightness-establishing cue early enough that the motion effect samples the intended state before visible travel starts

## Example Edit Workflow

When rebuilding a section or targeted window:

1. Use metadata tools to identify the exact `start_time` and `end_time`.
2. Call `cue.clear(start_time, end_time)`.
3. Call `cue.propose` with replacement entries that match the cue contracts above.
4. Call `cue.render` and inspect the rendered output or `backend/cues/{song}.dmx.log` if needed.
5. Confirm the resulting window contains only the intended cues and no stale carryover rows.
