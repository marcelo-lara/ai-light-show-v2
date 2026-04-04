
## Analyzer
### Init Song
- Init Song: add bpm and duration at the top of info.json. 
  - load the mp3 to get duration.
  - use a minimal model to get estimated bpm.

### Analyzer: Store reference and inference data in dedicated folders
- Store inferences at `analyzer/meta/{song}/infered/beats.{model_name}.json`.
- Store references at `analyzer/meta/{song}/reference/beats.json`.
- Keep references read-only and treat them as human-validated comparison data.
- Rationale: this is the foundation for comparing model outputs and choosing winners without overwriting canonical data.

### Find Chords Patterns
- If beats.json has chords data: find chord patterns and group them as chord_pattern.
  - use "Pet Shop Boys - I'm not scared" as example: "Cm|Fm|Cm|Fm" -> pattern A, "Ab-Bb|Cm|Ab-Bb|Cm" -> pattern B (there are 5 patterns in this song)
  - save these patterns in "analyzer/meta/{song}/chord_patterns.json" and add a reference to it in "analyzer/meta/{song}/info.json" (artifacts section)

### Stereo Analysis
- Analyze Left and Right channels to annotate significative diferences
  - notable example: 'Best Friend - Sofi Tukker', from 0.0 to 18.11 cymbals on the left channel, echoes and low frequencies on the right.

### Analyzer: Chords Finder
- Try alternative models and keep the best-performing winner.
- Dependency: reference/inference storage should land first so comparisons are reproducible.

### Analyzer: Sections Finder
- Try `https://github.com/MWM-io/SpecTNT-pytorch`.
- Try `https://huggingface.co/osheroff/SongFormer`.
- Dependency: reference/inference storage should land first so outputs can be evaluated against stable references.

### Analyzer: Song Loops regions
- Find patterns that repeat across the song, for example repeated drum or bass stem phrases while ignoring unrelated stems such as vocals.
- Rationale: useful, but exploratory and not required to stabilize current analyzer or frontend workflows.

### Analyzer: Nice to have
- UI to import reference or inference data into the canonical data.
  - Dependency: only worth building after the reference/inference folder model is in active use.

### Analyzer: Minimal UI
- Create a small internal UI to:
  - select song
  - manage task queue
  - view files
  - view plots


## Frontend

### Frontend: SongAnalysis left column
- resize: 'Song Loader' to 35% height and 'Analyzer Queue' to 65% height.

### Frontend: SongAnalysis > Plots 
- "analysis-card analysis-plots" must load ONLY when visible (DO NOT LOAD ALL svg artifacts when the page is selected)

### Feature: Reload song data from disk
- on 'song-loader-header' add a recycle icon to reload backend data from disk (all metadata to the selected song + refresh song list)

### Frontend: analyzer-queue-row
- analyzer-queue-row pending: progress bar should be 'empty' or hidden.
- on 'analyzer-queue-row-detail': 'pending: Waiting...' should be 'Waiting...' (remove status from the detail)

### Frontend: analyzer-queue-row
- analyzer-queue-row pending: progress bar should be 'empty' or hidden.
- on 'analyzer-queue-row-detail': 'pending: Waiting...' should be 'Waiting...' (remove status from the detail)

### Frontend: Reload song after Full Analysis
- Afer a full analysis, reload the song metadata from the backend (to include the new generated metadata)

## Backend
### Backend: Refactor DMX values
- Declare cue/chaser time units in beats and convert with `backend/services/cue_helpers/timing.py` via `beats_to_seconds`.
- Express dimmer intensity as float `0..1`, where `0` is off and `1` is full output.
- Rationale: this improves correctness and consistency, but it is a broad contract change that can touch helpers, chasers, rendering, tests, and documentation.
- Note: treat this as a coordinated backend change, not a quick patch.

### Backend: Add/Refine base fixture effects
- Moving heads: orbit 'dim' should be optional (calculate light by default, BUT allow to skip it). The goal is to combine the 'orbit' effect with other lighting patterns.

### Backend: Add new chasers / Refine current chasers
- TBD: 
  - effect 'circle': move moving heads around a POI. Parameters should be target_poi and radius. (calculate a circle based on cardinal references to estimate pan/tilt values using geometry, not just pan/tilt circles)
  - effect 'orbit_out': read 'orbit' to make the opposite direction (leave dimmer optional)
  - 'ba-bum ... rest': a heartbeat like effect.
  - 'drop-and-explode': dim out to blackout, and at the end (drop) dim to full.
  - 'vocal-stage-fade': From Xs to just before Ys, mini_beam_prism_l now moves to piano, mini_beam_prism_r moves to sofa, and both fade out across that vocal tail level. 
  - 'drop'
  - 'slow vocal'
  - 'drop buildup'
  - 'outro hit'
  - 'outro fade', 

