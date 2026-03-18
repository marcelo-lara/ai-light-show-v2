# Show Builder - Cue Sheet
A list of cue entries stacked in rows.
This Cue Sheet is stored in the cues list.

## Row detail
Each row is divided in three blocks

## 1. Select
Only availabe when:

1. Chase Builder is in "Create" mode.


## 2. Info 

- Effect row:
  - time: time when the effect will start
  - fixture: the fixture that will perform
  - effect: the effect that will be rendered on the fixture
  - duration: the total time the effect will require the fixture to perform
- Chaser row:
  - time: time when the chaser will start
  - chaser: the chaser name selected from `chaser_id`
  - duration: calculated from the chaser beat offsets, repetitions, and current BPM

## 3. Action Buttons

- delete: removes the cue entry
- preview:
  - effect row: executes the effect on the fixture in real-time
  - chaser row: executes the chaser preview in real-time
- edit:
  - effect row: expands cue entry in the effect picker to edit parameters
  - chaser row: expands cue entry in the chaser picker to edit chaser and repetitions

## LLM Hints

- [add your definitions here]
