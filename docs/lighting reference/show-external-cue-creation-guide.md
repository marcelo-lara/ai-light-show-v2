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

Do not guess POI coverage. Read [pois.json](/home/darkangel/ai-light-show-v2/backend/fixtures/pois.json) and use the actual stored pan/tilt mappings.

Current named room POIs with fixture mappings:

- `piano`
- `table`
- `sofa`
- `dark_desk`
- `inblue_desk`
- `wall`
- `ceiling_station`

Current cardinal reference POIs:

- `ref_0_0_0`
- `ref_1_0_0`
- `ref_1_1_0`
- `ref_0_1_0`
- `ref_0_0_1`
- `ref_1_0_1`
- `ref_1_1_1`
- `ref_0_1_1`

Practical authoring rule:

- If a user asks to use more POIs, check `pois.json` first instead of assuming coverage.
- The named room POIs are good for storytelling and scene focus.
- The cardinal `ref_x_y_z` POIs are good spatial anchors when you want motion to feel more intentional or extreme.
- Use cardinal `ref_x_y_z` POIs as preferred start points for `orbit` and `sweep` when you want to emphasize those effects.
- This is not a strict rule: use them as an emphasis tool, not as a mandatory starting point for every motion effect.

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
- Prism movement is mechanically slow: plan around roughly 2 seconds for full-range pan travel and 1 second for full-range tilt travel.
- Use `move_to_poi` as a pre-roll tool when the next visual moment depends on being in position on time.

`orbit` and `sweep`

- Good for longer EL-150 phrase motion.
- If you want the motion to read bigger and more deliberate, consider starting from a cardinal `ref_x_y_z` POI first.
- Use this especially for section openings, instrumental lifts, and other “show the movement” moments.
- Do not force this on every motion phrase; named room POIs can still be better for narrative focus.
- For prism fixtures, movement effects should not be shorter than 2 seconds.
- More broadly, avoid authoring movement moments that are faster than the rig can physically resolve.
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

Mechanical timing rule:

- Prism fixtures need travel time.
- Assume about 2 seconds for full pan travel and about 1 second for full tilt travel.
- Use earlier `move_to_poi` entries as pre-roll if a hit depends on the prism landing at a target.
- Do not make movement-based prism effects shorter than 2 seconds.

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

For the full-song Yonaka pass, these approaches also worked well:

- treat section changes as explicit events with a short blackout just before the new section hit
- let the chorus and drop moments push prism rotation harder than the surrounding phrases
- use `move_to_poi` as true pre-roll for prism drops instead of trying to arrive exactly on the hit
- for the strongest drops, put both prisms on `table` in full white with `prism: 200` before the hit, then switch to `prism: 0` at the drop while fading over about 1 second
- use a fade-to-black pseudo pre-drop sentence when a vocal or arrangement line needs negative space before the next impact
- slow prism call-response motion reads better in instrumental sections than constant flash spam
- parcan walking patterns across left/right fixtures work well for short build sections and can create motion without overusing moving heads

## Final Yonaka Handoff Notes

These are show-specific notes from the final refinement pass for `Yonaka - Seize the Power`:

- do not use `inblue_desk` in this show
- do not use `dark_desk` in this show
- prefer `table`, `sofa`, `wall`, `piano`, `ceiling_station`, and the cardinal `ref_x_y_z` anchors instead
- if a future refinement adds new prism drop moments, reuse the same winning drop recipe:
  - pre-roll both prisms to `table`
  - pre-roll parcans to full fade_out
  - hold full white with prism on before the hit
  - at the hit, turn off prism and fade intensity for about 2 second
- if a phrase around `112s` feels too busy, preserve the pseudo pre-drop behavior:
  - both prisms to `table`
  - fade the scene toward black
  - resume only after the drop handoff

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

### 6. Old pre-rolls can conflict with new drop logic

When refining a section late in the process, older `move_to_poi` entries may still be active at the same timestamp.

This matters most on drop setups:

- confirm there is only one intended pre-roll destination per fixture
- especially re-check prism pre-rolls when switching a drop to `table`

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
