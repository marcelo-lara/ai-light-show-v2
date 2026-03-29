# Show External Cue Creation Guide

This guide captures the repo-specific knowledge needed to author light show cues in this project without re-learning the system every session.

## What A Cue File Is

- Cue sheets live in `backend/cues/<Song Name>.json`.
- A cue file is a JSON array.
- Each item is either:
  - an effect cue entry:
    - `time`
    - `fixture_id`
    - `effect`
    - `duration`
    - `data`
    - optional `created_by`
  - or a chaser cue entry:
    - `time`
    - `chaser_id`
    - `data` with `repetitions`
    - optional `created_by`

Example effect entry:

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

Example chaser entry:

```json
{
  "time": 6.7,
  "chaser_id": "yonaka_intro",
  "data": {
    "repetitions": 4
  },
  "created_by": "chaser:yonaka_intro"
}
```

## Core Files To Read First

- Fixtures: [fixtures.json](/home/darkangel/ai-light-show-v2/backend/fixtures/fixtures.json)
- POIs: [pois.json](/home/darkangel/ai-light-show-v2/backend/fixtures/pois.json)
- Chasers: [chasers.json](/home/darkangel/ai-light-show-v2/backend/fixtures/chasers.json)
- Song beat/chord map: `analyzer/meta/<Song>/beats.json`
- Song sections: `analyzer/meta/<Song>/sections.json`
- Cue target: `backend/cues/<Song>.json`

For timing-heavy work, `beats.json` and `sections.json` are the most important sources.

## Current Fixture Inventory

Current fixed ids from [fixtures.json](/home/darkangel/ai-light-show-v2/backend/fixtures/fixtures.json):

- `head_el150`
- `mini_beam_prism_l`
- `mini_beam_prism_r`
- `parcan_l`
- `parcan_r`
- `parcan_pl`
- `parcan_pr`

Practical grouping:

- Moving head:
  - `head_el150`
- Prism moving heads:
  - `mini_beam_prism_l`
  - `mini_beam_prism_r`
- Inner RGB parcans:
  - `parcan_l`
  - `parcan_r`
- Outer proton parcans:
  - `parcan_pl`
  - `parcan_pr`

Useful left/right groups:

- Left side:
  - `mini_beam_prism_l`
  - `parcan_l`
  - `parcan_pl`
- Right side:
  - `mini_beam_prism_r`
  - `parcan_r`
  - `parcan_pr`

## POI Reality Check

Do not assume every fixture can use every POI.

Current meaningful POI coverage from [pois.json](/home/darkangel/ai-light-show-v2/backend/fixtures/pois.json):

- `head_el150`:
  - `piano`
  - `table`
- `mini_beam_prism_l`:
  - `piano`
  - `table`
  - `sofa`
  - `dark_desk`
- `mini_beam_prism_r`:
  - `piano`
  - `table`
  - `wall`

There are also reference POIs like `ref_0_0_0`, but unless a fixture has stored pan/tilt targets for them, `move_to_poi` will not be useful.

Important authoring rule:

- If a user asks to use more POIs, first check whether the target fixture actually has mappings in `pois.json`.
- In this repo, prism fixtures currently have more spatial variety than `head_el150`.

## Effects That Matter Most In Practice

Commonly useful effects in this project:

- `flash`
- `full`
- `fade_out`
- `fade_in`
- `blackout`
- `set_channels`
- `move_to_poi`
- `orbit`
- `sweep`

### Practical effect behavior notes

`flash`

- Best for punchy accents.
- On RGB fixtures, `data.color` works.
- On moving heads, `flash` mainly drives intensity; color wheel still needs separate `set_channels`.

`set_channels`

- This is the main tool for moving-head color/prism/gobo setup.
- Use it before a flash if you need:
  - prism on/off/rotate
  - color wheel changes
  - dim floor changes
  - gobo selection

`move_to_poi`

- Use for direct fixture-to-POI positioning.
- Only valid when the target fixture actually has that POI mapped.

`orbit` and `sweep`

- Good for longer EL-150 phrase motion.
- Avoid overlapping multiple pan/tilt effects on the same moving head at the same timestamp unless you intentionally want one to win.

`fade_out`

- Good for true release moments.
- Be careful with prism fixtures: if the creative note says “keep them alive,” a `fade_out` may kill too much presence.
- In practice, a low `set_channels` dim floor can be better than `fade_out`.

## Prism Meta-Channel Knowledge

From the mini beam fixture definition:

- `prism: 0` = off
- `prism: 130` = on
- `prism: 200` = rotate

This is important:

- If you want static split beams, use `130`.
- If you want aggressive high-energy prism motion, use `200`.
- Use `set_channels` to switch between those values.

Example:

```json
{
  "time": 84.18,
  "fixture_id": "mini_beam_prism_l",
  "effect": "set_channels",
  "duration": 0.0,
  "data": {
    "channels": {
      "color": 55,
      "prism": 200,
      "dim": 240,
      "strobe": 0
    }
  }
}
```

## Color Mapping Knowledge

Mini beam prism color wheel useful values:

- `55` = blue
- `65` = indigo
- `15` = red

Head EL-150 color wheel useful values:

- `150` = blue
- `175` = red
- `75` = purple

In practice:

- Use `55` / `150` for blue
- Use `65` for prism indigo
- Use `15` / `175` for red
- EL-150 does not have a true indigo slot, so purple is the closest wheel mood

## Timing Workflow

When writing a show from metadata:

1. Read `sections.json`
2. Read `beats.json`
3. Extract:
   - section starts/ends
   - bar starts
   - exact beat timestamps
   - chord changes if relevant
4. Build cue timing from actual timestamps, not from guessed BPM math alone

Preferred timing anchors:

- For arrangement logic:
  - section starts from `sections.json`
- For beat-accurate cueing:
  - exact beat times from `beats.json`
- For repeated motifs:
  - map by `bar` and `beat`, not by rough seconds

## Chaser Format

Chasers live in [chasers.json](/home/darkangel/ai-light-show-v2/backend/fixtures/chasers.json).

Schema shape:

```json
{
  "id": "example_id",
  "name": "Readable Name",
  "description": "What the chaser does",
  "effects": [
    {
      "beat": 0.0,
      "fixture_id": "parcan_l",
      "effect": "flash",
      "duration": 1.0,
      "data": {}
    }
  ]
}
```

Notes:

- `beat` is an offset inside the chaser pattern.
- `duration` is also in beats.
- Chaser cycle length is inferred from the maximum `beat + duration`.
- This means long trailing effects can accidentally stretch the chaser cycle.

Practical consequence:

- If you want a chaser to loop every 4 bars, watch the final event duration carefully.

## Reusable Authoring Pattern

When building a song from scratch, use this order:

1. Establish fixture groups
2. Check POI coverage
3. Read beat and section metadata
4. Decide the recurring motif
5. Decide what belongs in:
   - raw cues
   - reusable chasers
6. Author the intro first
7. Validate JSON
8. Spot-check exact timestamps the user cares about

## What Worked Well For Yonaka - Seize the Power

For this system, a good intro authoring strategy was:

- use actual beat timestamps
- use alternating left/right prism flashes
- pair each prism hit with opposite-side parcans
- use blue wheel/color as the anchor
- keep a low prism dim floor when the creative note says “don’t disappear”
- use a stronger overlapping “double punch” for cycle anchors
- save the repeated motif as a chaser once the pattern stabilizes

## Common Gotchas

### 1. Root-owned cue files

Some cue files may be owned by `root` while the directory is writable.

If direct write fails with permission denied:

- generate the replacement file elsewhere in the workspace
- remove the root-owned file
- move the regenerated file into place

Do not assume normal overwrite will work.

### 2. `flash` is not enough for moving-head color

If you need a prism or moving head to flash in blue/red/indigo:

- set the wheel color first with `set_channels`
- then trigger `flash`

### 3. POI assumptions break easily

Before using `move_to_poi`, confirm the fixture has that POI in `pois.json`.

### 4. Prism presence vs release

If the user says the prisms feel “too dim too much time,” check for:

- `fade_out` entries on prism fixtures
- `set_channels` dim floors that are too low

Sometimes a better solution is:

- keep `dim: 10` or higher when not blacked out
- reserve true `fade_out` for actual endings/releases

### 5. Duplicate same-time entries

When repeatedly editing cues by script, it is easy to stack multiple flashes for the same fixture/time.

Always inspect key timestamps after big changes.

## Minimal Verification Checklist

After any cue or chaser change:

1. Run JSON validation
2. Inspect exact requested timestamps
3. Confirm fixture ids are real
4. Confirm POIs are valid for the target fixture
5. Confirm prism values are intentional:
   - `0`
   - `130`
   - `200`

## Recommended Future Session Prompting

If a future session is asked to build a show, the fastest start is:

- read this guide
- inspect:
  - [fixtures.json](/home/darkangel/ai-light-show-v2/backend/fixtures/fixtures.json)
  - [pois.json](/home/darkangel/ai-light-show-v2/backend/fixtures/pois.json)
  - [chasers.json](/home/darkangel/ai-light-show-v2/backend/fixtures/chasers.json)
  - `analyzer/meta/<Song>/beats.json`
  - `analyzer/meta/<Song>/sections.json`
- then author from real beat times, not guesses

That avoids almost all of the re-discovery work.
