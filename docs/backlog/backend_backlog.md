
## BUG: Song Draft Helper is failing

## Refactor DMX values
- time units must be declared as beats: transform beats to seconds using backend/services/cue_helpers/timing.py (beats_to_seconds)
- dimmer intensity must be expressed as float 0 to 1: where 0 is no light (0) and 1 is full light (255).