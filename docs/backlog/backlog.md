## Analyzer

### Song Loops regions
- Find patterns that repeat across the song. example: drum pattern that repeats in drum stem, ignoring the vocal stem. The same for bass and other stems.

### Sections Finder
- Try this implementation https://github.com/MWM-io/SpecTNT-pytorch
- Try this https://huggingface.co/osheroff/SongFormer

### Chords Finder


### Store reference/inferences in dedicated folders
- store inferences at analyzer/meta/{song}/infered/beats.{model_name}.json
- store references (source of truth) at analyzer/meta/{song}/reference/beats.json
  - references is human-validated data: it should be read-only; used to compare with the infered values.

### NiceToHave: 
- UI to import reference/inference data into the actual data.

### (?) Self-Repo
- If so, create a small UI to:
  - select song
  - manage tasks queue
  - view files
  - view plots (plotly?)

## Backend

### BUG: Song Draft Helper is failing

### Refactor DMX values
- time units must be declared as beats: transform beats to seconds using backend/services/cue_helpers/timing.py (beats_to_seconds)
- dimmer intensity must be expressed as float 0 to 1: where 0 is no light (0) and 1 is full light (255).