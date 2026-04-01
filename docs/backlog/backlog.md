## Analyzer

### Song Loops regions
- Find patterns that repeat across the song. example: drum pattern that repeats in drum stem, ignoring the vocal stem. The same for bass and other stems.

### Sections Finder
- Try this implementation https://github.com/MWM-io/SpecTNT-pytorch
- Try this https://huggingface.co/osheroff/SongFormer

### Chords Finder
- Try other models: challenge and keep the winner alternative.

### Store reference/inferences in dedicated folders
- store inferences at analyzer/meta/{song}/infered/beats.{model_name}.json
- store references (source of truth) at analyzer/meta/{song}/reference/beats.json
  - references is human-validated data: it should be read-only; used to compare with the infered values.

### Add TASK_TYPES endpoint
- expose a list of TASK_TYPES, so clients can display it.
- add 'description' to the TASK_TYPES.

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
- Fix this helper

### Refactor DMX values
- time units must be declared as beats: transform beats to seconds using backend/services/cue_helpers/timing.py (beats_to_seconds)
- dimmer intensity must be expressed as float 0 to 1: where 0 is no light (0) and 1 is full light (255).

## Frontend

### SongAnalysis > Analyzer Queue
- Create a collapsible Actions menu with checkboxes.
  - When collapsed it has to display "Analyze Song ⌃"
  - When expanded, a list of tasks (to enqueue in the Analyzer module) with the "Add to Queue", "Run All", and "Remove All"
  - The actions list should be retrieved from the backend (that will be rertieved by the backend from the analyzer module)
- The items on the queue should be scrollable.