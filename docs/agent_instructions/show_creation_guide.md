# Show External Cue Creation Guide For LLMs

This document is the artistic reference for creating or refining a show in this repo. Use it to interpret the song, define palette and fixture roles, and turn musical evidence into a readable visual plan.

For cue schema, MCP workflow, fixture IDs, effect payloads, POI validation, chaser timing mechanics, and render validation, use [cue_sheet_guide.md](./cue_sheet_guide.md).

## Scope

This guide owns:

- creative reading order for song artifacts
- the visual strategy written into `lighting_score.md`
- palette, phrasing, and section identity
- fixture-role storytelling
- reusable artistic patterns for common song shapes

This guide does not own low-level cue contracts.

## Goal

For any song, produce:

- a canonical analysis brief at `data/output/<Song>/lighting_score.md`
- a cue sheet at `backend/cues/<Song>.json`

The lighting score explains the artistic plan. The cue sheet implements that plan through the technical contract in [cue_sheet_guide.md](./cue_sheet_guide.md).

## Required Iteration Behavior

When refining an existing song:

- always update `data/output/<Song>/lighting_score.md`
- always update `backend/cues/<Song>.json`
- update this guide when a reusable artistic rule emerges
- rebuild section ideas as clean phrase windows rather than stacking new concepts on top of stale material

Legacy planning briefs such as `data/artifacts/<Song>/<Song>.md` are optional reference material only. Do not treat them as canonical when `data/output/<Song>/lighting_score.md` exists.

## Creative Reading Order

Read these first:

- canonical analysis brief: `data/output/<Song>/lighting_score.md`
- curated musical hints: `data/reference/<Song>/human/human_hints.json`
- Essentia FFT band detail: `data/artifacts/<Song>/essentia/fft_bands.json`
- merged feature IR: `data/artifacts/<Song>/music_feature_layers.json`
- harmonic layer: `data/artifacts/<Song>/layer_a_harmonic.json`
- symbolic layer: `data/artifacts/<Song>/layer_b_symbolic.json`
- energy layer: `data/artifacts/<Song>/layer_c_energy.json`
- song beats: `data/output/<Song>/beats.json`
- song sections: `data/output/<Song>/sections.json`

Optional context when it matters:

- `data/output/<Song>/info.json`
- `data/artifacts/<Song>/chord_patterns.json`
- `data/artifacts/<Song>/features.json`
- `data/artifacts/<Song>/hints.json`
- `data/artifacts/<Song>/*_loudness_envelope.json`
- `data/artifacts/<Song>/<Song>.md`

Interpretation priorities:

- use Human Hints to anchor intention, motif importance, and section-specific meaning
- use `fft_bands.json` to understand spectral density, brightness, and where fixture layering should respond to the mix
- trust `beats.json` and `sections.json` first when the phrasing boundary matters
- consult loudness envelopes when the emotional rise and fall matters
- inspect `chord_patterns.json` before inventing a harmonic story that the artifacts do not support
- if `lighting_score.md` and older planning notes disagree, reconcile toward the canonical metadata artifacts

## Deliverables

### Canonical Analysis Brief

Create or update `data/output/<Song>/lighting_score.md` with:

- feature summary
- high-level visual strategy
- fixture intentions
- section-by-section plan
- loudness, dip, build, and drop observations
- any song-specific rules that should guide later cue edits

Keep the brief aligned with `music_feature_layers.json`. When section evidence, harmonic motion, symbolic phrasing, or energy detail matters, pull it from the artifacts rather than inventing unsupported structure.

### Cue Sheet Intent

Create or update `backend/cues/<Song>.json` so the cue sheet clearly expresses the current artistic plan. Use [cue_sheet_guide.md](./cue_sheet_guide.md) to choose the exact cue structure and effect payloads.

## Fixture Roles In The Show

Treat fixture families as visual roles rather than just hardware groups:

- prism moving heads: impact, emotional release, mirrored width, kinetic energy
- `head_el150`: phrase narrator, center focus, transition glue, vocal anchor
- inner parcans: rhythmic chatter, stereo detail, local color support
- outer parcans: width, weight, and downbeat reinforcement

Keep those roles stable enough that recurring sections feel related rather than randomly reassigned.

## Spatial Storytelling

Use space as part of the composition:

- room POIs read as story locations and focal subjects
- reference-cube POIs read as geometry, arcs, and deliberate movement shapes
- voice-led phrases often benefit from one shared anchor for all moving heads
- decide whether a phrase should read as `converge` or `diverge`, then keep that logic consistent through the phrase
- let the center fixture feel intentional; do not let it drift into an accidental left-right role

## Palette And Visual Language

When choosing a palette:

- pick the main color family from the prism look first
- keep parcan colors analogous to that family instead of competing with it
- reserve white for punctuation, drops, and endings
- when a short chord loop repeats through multiple sections, keep one stable chord-color identity and escalate later passes with width, motion, or accent density rather than replacing the palette each time

## Translating Music Into Light

Translate song evidence into fixture behavior like this:

- low-energy bars: dimmer, slower, more spacious
- rising bars: brighter, more assertive, more open
- drops: remove energy before the hit, then release it decisively
- vocal-led sections: fewer hits, slower motion, clearer focus
- electronic or instrumental sections: more kinetic, more rhythmic, more extroverted

When `chord_patterns.json` exists:

- repeated chord patterns should usually produce repeated visual phrases
- let the strongest recurring pattern define the section's default loop language
- use pattern changes as likely points for palette shifts, motion resets, or fixture-role swaps
- if two sections share the same pattern but differ in energy, evolve the same idea instead of replacing it with an unrelated one

## How To Build A Show

Use this artistic workflow:

1. Read the musical artifacts in the order above.
2. Write or revise the canonical analysis brief in `data/output/<Song>/lighting_score.md`.
3. Divide the song into phrase-aligned authoring windows of about 60 seconds. Prefer section boundaries when they fit; split longer sections into multiple phrase windows.
4. Decide the palette, recurring motion language, and fixture-role balance for each window.
5. Decide which ideas should recur as motifs and which should remain unique to a phrase.
6. Express those decisions in the cue sheet using [cue_sheet_guide.md](./cue_sheet_guide.md).
7. After each rewritten window, verify that the resulting cues still read like the intended artistic idea before moving on.

## Section Identity Patterns

### Voice-Driven Sections

When a section is voice-driven rather than beat-driven:

- keep motion slower and more phrase-based
- reduce flash density
- prefer grounded movement and stable focus
- let `head_el150` carry the sentence while the prisms support it

For strongly vocal-led phrases:

- give all moving heads one shared anchor idea
- keep the phrase legible as either a clean convergence or a clean divergence
- let the anchor land before changing it
- if the phrase feels muddled, rebuild the whole moving-head phrase window around one anchor logic

### High-Energy Ignition Bars

When a section or bar is marked as a major hit:

- start the pre-drop early enough to create tension
- simplify the room before the reopening
- let the moving fixtures lead the release on the ignition bar
- allow the prism layer to become wider, brighter, or more rotational than the surrounding material

### Loudness Drop-Then-Rise Moments

If a loudness envelope shows a dip followed by an explosion:

- thin the room during the dip
- let the moving heads drive the first moment of release
- widen the room afterward with the parcan layer

## Reusable Artistic Patterns

### Drop Prep Pattern

When a notable drop is led by a short vocal-only or low-density window:

- treat that window as one coherent tension phrase
- dim the room progressively before the hit
- let `head_el150` carry the line while the rest of the rig pulls back
- reopen the drop with a clear, readable burst from the moving-head layer before the wider rig fills in

### Outro Closure Pattern

For endings:

- resolve the moving-head focus toward a final room subject rather than ending mid-thought
- taper the room into a readable release instead of a hard cutoff
- make the final state feel conclusive, not simply dimmer

### Color Palette Pattern

When choosing colors across a whole song:

- choose the primary emotional color family early
- let recurring sections return to that identity unless the song evidence clearly argues for a break
- use contrast colors sparingly so the main palette still reads as intentional

## Chaser Use As A Creative Choice

Use chasers when:
- a repeated motif should feel stable across several bars
- the phrase is truly reusable
- harmonic repetition supports a recurring visual grammar

### Chaser Scoping
- **Global Chasers**: Use for generic utilities (e.g., `parcan_wave_lr`, `strobe_pulse`). These should not reference specific POIs unless they are universal (like `center`).
- **Song-Specific Chasers**: Use for motifs that define the song's identity (e.g., `chimera_vocal_tail`). These are stored within the song's cue file and can safely reference any POI or fixture role specific to that track.

Prefer direct phrase design when:
- the section has unique phrasing
- the emotional shape changes bar by bar
- the section needs a one-off narrative gesture rather than a looping motif

## Default Artistic Authoring Contract

If you are the model creating or refining a show:

- read the song metadata before writing cues
- revise `lighting_score.md` before or alongside the cue sheet
- author long shows one phrase window at a time
- keep fixture roles distinct and readable
- let low-energy parts breathe
- make rises, drops, and returns legible
- update the artistic brief when the creative direction changes

This avoids rediscovering the same show logic every session.
