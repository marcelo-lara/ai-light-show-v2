
## Analyzer

### Analyzer: Chords Finder
- Try alternative models and keep the best-performing winner.
- Dependency: reference/inference storage should land first so comparisons are reproducible.

### Analyzer: Sections Finder
- Try `https://github.com/MWM-io/SpecTNT-pytorch`.
- Try `https://huggingface.co/osheroff/SongFormer`.
- Dependency: reference/inference storage should land first so outputs can be evaluated against stable references.


## Frontend

### Frontend: SongAnalysis left column
- resize: 'Song Loader' to 35% height and 'Analyzer Queue' to 65% height.

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
  - 'ba-bum ... rest': a heartbeat like effect.
  - 'drop-and-explode': dim out to blackout, and at the end (drop) dim to full.
  - 'vocal-stage-fade': From Xs to just before Ys, mini_beam_prism_l now moves to piano, mini_beam_prism_r moves to sofa, and both fade out across that vocal tail level. 
  - 'drop'
  - 'slow vocal'
  - 'drop buildup'
  - 'outro hit'
  - 'outro fade', 

