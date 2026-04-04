# Show External Cue Creation Guide For LLMs

This document is the generic authoring guide for language models working in this repo. Use it to create new shows, refine existing shows, and keep the planning and cue artifacts aligned.

## Goal

For any song, produce:

- a planning brief at `analyzer/meta/<Song>/<Song>.md`
- a cue sheet at `backend/cues/<Song>.json`

The planning brief explains the creative plan. The cue sheet implements it.

## Required Iteration Behavior

When refining an existing song:

- always update `analyzer/meta/<Song>/<Song>.md`
- always update `backend/cues/<Song>.json`
- update this guide when a rule becomes reusable across songs
- clear the cue time window for the section being rebuilt before recreating that section

Do not stack new ideas on top of stale cues for the same section.

## Core Files To Read First

- Fixtures: [fixtures.json](/home/darkangel/ai-light-show-v2/backend/fixtures/fixtures.json)
- POIs: [pois.json](/home/darkangel/ai-light-show-v2/backend/fixtures/pois.json)
- Chasers: [chasers.json](/home/darkangel/ai-light-show-v2/backend/fixtures/chasers.json)
- Song beats: `analyzer/meta/<Song>/beats.json`
- Song sections: `analyzer/meta/<Song>/sections.json`
- Optional song metadata:
  - `analyzer/meta/<Song>/info.json`
  - `analyzer/meta/<Song>/chord_patterns.json`
  - `analyzer/meta/<Song>/features.json`
  - `analyzer/meta/<Song>/hints.json`
  - `analyzer/meta/<Song>/*_loudness_envelope.json`

If timing matters, trust `beats.json` and `sections.json` first. If motion and emotional rise/fall matter, also inspect `*_loudness_envelope.json`.
If harmonic repetition matters, inspect `chord_patterns.json` before inventing your own progression map.

## Deliverables

### 1. Planning Brief

Create `analyzer/meta/<Song>/<Song>.md` with:

- feature summary
- high-level visual strategy
- fixture intentions
- section-by-section plan
- loudness, dip, build, and drop observations
- any song-specific rules that should guide later cue edits

### 2. Cue Sheet

Create or update `backend/cues/<Song>.json` as a JSON array of cue entries.

Each cue is usually:

```json
{
  "time": 1.36,
  "fixture_id": "mini_beam_prism_l",
  "effect": "flash",
  "duration": 1.32,
  "data": {},
  "created_by": "codex:example"
}
```

Chaser entries are also allowed:

```json
{
  "time": 6.7,
  "chaser_id": "example_chaser",
  "data": {
    "repetitions": 4
  },
  "created_by": "chaser:example"
}
```

## Fixture Inventory

Current fixture ids from [fixtures.json](/home/darkangel/ai-light-show-v2/backend/fixtures/fixtures.json):

- `head_el150`
- `mini_beam_prism_l`
- `mini_beam_prism_r`
- `parcan_l`
- `parcan_r`
- `parcan_pl`
- `parcan_pr`

Practical groups:

- `head_el150`: phrase narrator
- `mini_beam_prism_l`, `mini_beam_prism_r`: energy, drops, room focus
- `parcan_l`, `parcan_r`: inner rhythmic detail
- `parcan_pl`, `parcan_pr`: wider stage reinforcement

Useful side groups:

- left: `mini_beam_prism_l`, `parcan_l`, `parcan_pl`
- right: `mini_beam_prism_r`, `parcan_r`, `parcan_pr`

## POI Rules

Do not guess POIs. Read [pois.json](/home/darkangel/ai-light-show-v2/backend/fixtures/pois.json) and only use mapped POIs for the target fixture.

Common named room POIs:

- `piano`
- `table`
- `sofa`
- `dark_desk`
- `inblue_desk`
- `wall`
- `ceiling_station`

Cardinal reference POIs:

- `ref_0_0_0`
- `ref_1_0_0`
- `ref_1_1_0`
- `ref_0_1_0`
- `ref_0_0_1`
- `ref_1_0_1`
- `ref_1_1_1`
- `ref_0_1_1`

Practical usage:

- named room POIs are best for storytelling and room focus
- `ref_x_y_z` POIs are best for deliberate sweeps, circles, orbits, and spatially bold motion
- prefer `ref_x_y_z` starts for `sweep` and `orbit` when you want the movement itself to read clearly
- `circle` depends on POI `location` data plus `ref_x_y_z` references, so keep its `target_poi` on a real room POI and let the reference cube define the motion geometry
- for grounded or voice-led motion, prefer lower-plane `z=0` POIs when the mapping supports it

## Effects You Will Use Most

Most useful effects:

- `set_channels`
- `flash`
- `full`
- `fade_in`
- `fade_out`
- `blackout`
- `move_to_poi`
- `circle`
- `orbit`
- `orbit_out`
- `sweep`

Practical notes:

### `set_channels`

- use it to set wheel color, prism state, gobo, dim floor, shutter, or other non-positional channels
- on moving heads, use `set_channels` before `flash` when the color or gobo matters

### `flash`

- use for impacts and rhythmic punctuation
- on RGB fixtures, color can be set directly in the flash payload when supported
- on moving heads, do not rely on `flash` alone for color changes
- if the fixture should feel continuously present through a harmonic section, do not fake that with repeated flashes; use held color states and reserve `flash` for actual accents

### `full` and `fade_in` on RGB fixtures

- use `full` to establish a sustained RGB bed at the start of a harmonic window
- use `fade_in` on the final beat before the next chord when the room should glide into the new color instead of snapping or flashing
- when using this pattern, clear any older per-beat RGB flash cues from the rebuilt time window so the sustained bed remains the only active parcan language

### `move_to_poi`

- use for direct positioning and pre-roll
- only use valid mapped POIs
- prism fixtures are mechanically slow, so pre-position them before the hit

### `circle`

- use it when you want moving heads to orbit around a room focus in world space rather than drawing a DMX-space circle
- required payload: `target_poi`, `radius`
- optional payload: `orbits`
- `target_poi` should usually be a named room POI with a real `location`; the reference cube POIs drive the interpolation behind the scenes
- keep `radius` modest so the motion reads as a controlled ring around the subject rather than a full-room sweep
- `circle` is motion-first: if the fixture should stay visibly on while moving, the show designer must author the dimmer behavior separately with `set_channels`, `full`, `fade_in`, `flash`, or overlapping cues

### `sweep` and `orbit`

- use sweep mainly on `head_el150`, and orbit on `mini_beam_prism_l` and `mini_beam_prism_r` for phrase motion
- these are best for section openings, vocal phrasing, instrumental arcs, and deliberate movement moments
- avoid piling multiple pan/tilt actions on the same fixture at the same timestamp unless one is intentionally replacing another
- `orbit` accepts `write_dimmer: false` when you want the movement to layer under another lighting pattern without forcing a blackout/preroll dim change
- when `write_dimmer: false`, the motion effect will not manage brightness for you; keeping the beam visible during travel is the show designer's responsibility

### `orbit_out`

- use it as the inverse of `orbit`: start on the subject and spiral back out toward `start_POI`
- it uses the same payload shape as `orbit`: `subject_POI`, `start_POI`, optional `orbits`, optional `easing`, optional `write_dimmer`
- this is useful for releases, phrase exits, or taking focus away from a vocal anchor without a hard snap
- like `orbit`, `orbit_out` may be used as motion-only by disabling dimmer writes, which means the show designer must pair it with intentional dimmer cues if light should remain present during the move

### `fade_out`

- use for true release, closure, or intentional space
- avoid overusing it on prisms when the creative direction is “stay alive but restrained”

## Mechanical Timing Rules

- build timing from actual beat timestamps, not guessed BPM math
- prism travel needs time
- assume roughly 2 seconds for full pan travel and 1 second for full tilt travel on prism fixtures
- do not author prism movement phrases shorter than 2 seconds unless the move is very small
- if a hit depends on a prism landing somewhere, schedule the `move_to_poi` early

## Color And Channel Knowledge

### Mini Beam Prism

Useful color wheel values:

- `55` = blue
- `65` = indigo
- `15` = red

Prism channel values:

- `0` = off
- `130` = on
- `200` = rotate

Practical guidance:

- use `130` for static split-beam texture
- use `200` for stronger high-energy motion
- blue/indigo palettes work especially well on the prisms

### Head EL-150

Useful color wheel values:

- `150` = blue
- `175` = red
- `75` = purple

Current gobo wheel values:

- `0` = `Open`
- `12` = `Tunnel`
- `24` = `BigOval`
- `36` = `SmallOval`
- `48` = `Squares`
- `60` = `Shapes`
- `72` = `Tribal`
- `84` = `Slashes`

Practical guidance:

- prefer only `Open` or `Tunnel` unless a song-specific note explicitly asks for another gobo
- `Tunnel` is `12`, not `25`
- EL-150 has no true indigo wheel slot, so purple is the closest moody companion to prism indigo

### RGB And Proton Parcans

Generic guidance:

- choose parcan colors as analogous companions to the prism palette
- if prisms live in blue / indigo, keep parcans in blue / indigo / azure territory
- if prisms live in pink / magenta / indigo, keep parcans adjacent rather than fighting the palette

## Generic Creative Translation Rules

Translate song analysis into fixture behavior like this:

- low energy bars: dimmer, slower, more spacious
- rising bars: brighter, more assertive, more open
- drops: remove energy before the hit, then release it decisively
- vocal-led sections: fewer hits, slower motion, more focus
- electronic or instrumental sections: more kinetic, more rhythmic, more extroverted

If `chord_patterns.json` exists, use it to stabilize the visual language:

- repeated chord patterns should usually produce repeated visual phrases unless the section notes give a clear reason to break that symmetry
- let the strongest recurring pattern define the section's default loop language for motion, color, or impact density
- use pattern changes as likely cue points for palette shifts, fixture-role swaps, or phrase resets
- if two sections share the same chord pattern but differ in energy, keep the structural idea related while changing brightness, density, width, or motion size
- do not infer a more complicated harmonic story than the artifact supports; when `chord_patterns.json` is absent, fall back to `beats.json`, `sections.json`, and other analyzer metadata

Useful fixture roles:

- prisms: impact, drop language, emotional release
- `head_el150`: phrase narrator, glue, section transitions
- inner parcans: chatter, syncopation, stereo detail
- outer parcans: width, weight, downbeat reinforcement

## How To Build A Show

Use this order:

1. Read fixture and POI definitions.
2. Read `sections.json` and `beats.json`.
3. Read the song metadata files that matter for energy, loudness, harmony, or hints.
4. Write the planning brief in `analyzer/meta/<Song>/<Song>.md`.
5. Decide the palette and recurring motion language.
6. Decide which ideas belong in raw cues and which belong in chasers.
7. Build the cue sheet in `backend/cues/<Song>.json`.
8. Validate JSON.
9. Spot-check exact timestamps, especially the ones the user called out.

## Section Identity Patterns

### Voice-Driven Sections

When a section is voice-driven rather than beat-driven:

- keep motion slower and more phrase-based
- reduce flash density
- prefer grounded `z=0` moving-head ideas when possible
- let `head_el150` carry the sentence while prisms support it elegantly

For strongly vocal-led phrases:

- give all moving heads one shared anchor POI
- use that anchor as the same `start_POI` or the same `target_POI`
- choose one of two clear reads:
  - `converge`: all moving heads go to the same POI
  - `diverge`: the phrase starts from the same anchor, then the moving heads split outward
- make the phrase readable: let the anchor idea land clearly before changing it
- avoid half-split targeting that does not read cleanly as converge or diverge
- if tightening an existing show, rebuild the whole moving-head phrase window so the anchor logic is consistent through the phrase

### High-Energy Ignition Bars

When a section or bar is marked as a major hit:

- start the pre-drop about 2 bars earlier unless the song note says otherwise
- use those bars to simplify the room and compress the rhythm
- let the moving fixtures lead the reopening on the ignition bar
- allow prisms to get brighter, wider, or more rotational than the surrounding material

### Loudness Envelope Rule

If `*_loudness_envelope.json` shows a drop-then-rise pattern, treat it as a likely emotional cue point:

- on the drop bar, thin the room and reduce motion density
- on the explode bar, let prisms and `head_el150` drive the release first
- then let the parcans widen and reinforce it

### Chord Pattern Rule

If `chord_patterns.json` is available:

- treat each recurring chord pattern as a candidate visual phrase unit
- prefer reusing one readable cue idea across repeated occurrences of the same pattern instead of rebuilding every bar from scratch
- when a pattern spans multiple bars, make the lighting phrase read across the whole pattern window rather than only on downbeats
- let pattern boundaries help decide where to reset motion, change POIs, rotate prism state, or swap between narration and rhythmic detail
- if a pattern repeats under different section energy, evolve the same idea rather than replacing it with unrelated motion
- if the artifact shows only short or weak patterns, do not force a loop; use sections and loudness as the stronger guide

## Reusable Winning Patterns

### Drop Prep Pattern

When a notable drop is led by a short vocal-only or low-density window:

- clear that window and rebuild it as one phrase
- start dimming several bars before the hit if the arrangement already thins out
- black out or fade out almost everything except `head_el150`
- let `head_el150` carry the line at about half intensity
- prefer `Tunnel` on `head_el150` for that tension phase
- at the drop bar, let both prisms start with a strong white hit before the wider rig opens again

### Outro Closure Pattern

For every song:

- on the outro or end-of-song release, point the moving heads to `table`
- close with `fade_out`
- make the closing `fade_out` at least 1 second long
- if refining the ending, clear that ending window first and rebuild it cleanly

Practical note:

- the POI part mainly applies to `head_el150`, `mini_beam_prism_l`, and `mini_beam_prism_r`
- parcans only need the closing fade behavior

### Color Palette Pattern

When choosing colors:

- choose the main palette from the prism wheel first
- then choose analogous colors for the parcans
- save white for punctuation, drops, and endings

## Chasers

Chasers live in [chasers.json](/home/darkangel/ai-light-show-v2/backend/fixtures/chasers.json).

Important schema facts:

- chaser `effects[].beat` is an offset inside the pattern
- chaser `effects[].duration` is also in beats
- the total cycle length is inferred from the largest `beat + duration`
- always calculate that cycle length before using a chaser as a bar-aligned motif; some chasers intentionally spill past beat 4, so only use them when that non-bar loop length is part of the design
- if the motif needs a breath before the next repetition, end the pattern with an explicit fade or reset so the inferred cycle length lands exactly on the intended beat boundary

Use chasers when:

- a repeated motif stabilizes across several bars
- the pattern is truly reusable
- `chord_patterns.json` confirms a harmonic phrase that should recur with the same visual grammar

Prefer raw cues when:

- the section has unique phrasing
- the motion or energy shape changes bar by bar

## Common Mistakes

### 1. Guessing POI coverage

Always verify POIs in [pois.json](/home/darkangel/ai-light-show-v2/backend/fixtures/pois.json).

### 2. Using `flash` without setting moving-head color first

If a moving head must flash in a specific color, set the wheel first with `set_channels`.

### 3. Making prism movement too fast

Prisms need travel time. Pre-roll the move.

### 4. Leaving old cues alive after a rebuild

If you refine a section but do not clear its old cues first, stale motion or pre-rolls may fight the new idea.

### 5. Duplicate same-time entries

Scripted edits can accidentally stack multiple entries for the same `time + fixture_id + effect`. Inspect key timestamps after big changes.

### 6. Killing prism presence by mistake

If the note is “restrained” rather than “gone,” a low dim floor may be better than `fade_out`.

### 7. Root-owned cue files

If direct overwrite fails because the file is owned by `root`:

- write a replacement file elsewhere
- remove the old file
- move the new one into place

## Minimal Verification Checklist

After any meaningful change:

1. Validate JSON.
2. Inspect the exact timestamps the user cared about.
3. Confirm fixture ids are real.
4. Confirm POIs are valid for each target fixture.
5. Confirm prism values are intentional: `0`, `130`, or `200`.
6. Check for duplicate same-time `fixture_id + effect` entries.
7. Confirm the ending obeys the `table + fade_out >= 1s` rule.

## Default LLM Authoring Contract

If you are the model creating or refining a show:

- read the song metadata before writing cues
- write the planning brief before or alongside the cue sheet
- use real timestamps
- keep fixture roles distinct
- let low-energy parts breathe
- make rises and drops legible
- update the song brief when the creative direction changes
- update this guide when you discover a rule that should apply to future songs

This avoids rediscovering the same workflow every session.
