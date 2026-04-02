## Prioritization

### [DONE] P0 - Fix breakage and remove duplicated contracts

#### Backend: Song Draft Helper is failing
- Fix this first.
- Rationale: this is an active bug on a backend-owned helper that already has direct test coverage and is part of the cue generation workflow.

#### Analyzer: Add TASK_TYPES endpoint
- Expose the analyzer task catalog so clients can display it.
- Add `description` to each task type.
- Align backend/frontend task handling to this single source of truth instead of hardcoded task lists.
- Rationale: the analyzer, backend, and frontend currently carry duplicated task catalogs, which is already causing capability drift.

### P1 - Complete the analyzer queue flow end to end

#### Frontend: SongAnalysis > Analyzer Queue
- Replace the single-select action picker with a collapsible Actions menu with checkboxes.
- When collapsed, display `Analyze Song ⌃`.
- When expanded, show the task list retrieved from the backend, plus `Add to Queue`, `Run All`, and `Remove All`.
- Make queue items scrollable.
- Dependency: do this after the TASK_TYPES endpoint exists so the UI is backend-driven.

#### Analyzer
- store bpm value in analyzer/meta/{song}/info.json

#### Feature: Reload song data from disk
- on 'song-loader-header' add a recycle icon to reload backend data from disk (all metadata to the selected song + refresh song list)

#### Frontend: SongAnalysis > Analyzer Queue
- show a line (of 1px) at the bottom of each task to show the progress of the task.
- when a task is marked as "complete" the line should be colored as '--ok', when error as '--err'

#### Frontend: SongAnalysis > Analyzer Queue 
- UI only: when 'run all' is clicked, close the 'analyzer-queue-actions' subpanel.

#### Frontend: SongAnalysis > Analyzer Queue 
- "analysis-card analysis-plots" must load ONLY when visible (DO NOT LOAD ALL when the page is selected)

#### Analyzer: Store reference and inference data in dedicated folders
- Store inferences at `analyzer/meta/{song}/infered/beats.{model_name}.json`.
- Store references at `analyzer/meta/{song}/reference/beats.json`.
- Keep references read-only and treat them as human-validated comparison data.
- Rationale: this is the foundation for comparing model outputs and choosing winners without overwriting canonical data.

### P2 - Normalize core cue contracts carefully

#### Backend: Refactor DMX values
- Declare cue/chaser time units in beats and convert with `backend/services/cue_helpers/timing.py` via `beats_to_seconds`.
- Express dimmer intensity as float `0..1`, where `0` is off and `1` is full output.
- Rationale: this improves correctness and consistency, but it is a broad contract change that can touch helpers, chasers, rendering, tests, and documentation.
- Note: treat this as a coordinated backend change, not a quick patch.

#### Backend: Add/Refine base fixture effects
- Moving heads: orbit 'dim' should be optional (calculate light by default, BUT allow to skip it). The goal is to combine the 'orbit' effect with other lighting patterns.

#### Backend: Add new chasers / Refine current chasers
- TBD: 'drop', 'slow vocal', 'drop buildup', 'outro hit', 'outro fade', 


### P3 - Improve analyzer model evaluation

#### Analyzer: Chords Finder
- Try alternative models and keep the best-performing winner.
- Dependency: reference/inference storage should land first so comparisons are reproducible.

#### Analyzer: Sections Finder
- Try `https://github.com/MWM-io/SpecTNT-pytorch`.
- Try `https://huggingface.co/osheroff/SongFormer`.
- Dependency: reference/inference storage should land first so outputs can be evaluated against stable references.

### P4 - R&D and tooling

#### Analyzer: Song Loops regions
- Find patterns that repeat across the song, for example repeated drum or bass stem phrases while ignoring unrelated stems such as vocals.
- Rationale: useful, but exploratory and not required to stabilize current analyzer or frontend workflows.

#### Nice to have
- UI to import reference or inference data into the canonical data.
- Dependency: only worth building after the reference/inference folder model is in active use.

#### Optional: Self-Repo
- If needed, create a small internal UI to:
  - select song
  - manage task queue
  - view files
  - view plots
- Rationale: this is last because it adds maintenance surface without resolving a current product gap.

## Recommended execution order

1. Fix Song Draft Helper.
2. Add analyzer TASK_TYPES endpoint with descriptions and make it the shared contract.
3. Finish the SongAnalysis analyzer queue UI on top of that contract.
4. Add reference/inference storage separation.
5. Run chord and section model bake-offs using that storage layout.
6. Perform the DMX value refactor as a dedicated coordinated change.
7. Revisit loop detection, import UI, and any Self-Repo tooling.