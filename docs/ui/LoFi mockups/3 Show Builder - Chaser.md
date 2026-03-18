# Show Builder - Chaser

## Definition

- A Chase is a sequence of effects to be re-used in any part of the song.
- Chaser times are expressed in **beats**.
- Chaser cue rows in the cue sheet store `chaser_id` and optional `data.repetitions`.
- The Chaser UI could be in one of these modes:
  - Apply Mode: user selects, preview, then add to cue sheet.
  - Edit Mode: allow the user to edit an existing chaser cue row.
  - Create Mode: allows to create a new chaser based on selected cue sheet entries.

## Modes Definitions

## Apply Mode - User Flow

1. The user seeks the song to the desired position.
2. The user selects one chaser from the dropdown.
   - the chaser effects list is displayed.
   - the list is reference/preview information only; it is not written as individual cue rows.
   - the 'Add' and 'Preview' buttons are displayed.
3. The user click 'Preview' to render the chaser direct to the artnet node (preview)
4. The user click 'Add' to persist one chaser cue row at the current song position.
5. The cue row stores the chaser id and repetitions, and duration is calculated from the chaser beats plus current BPM.

## Edit Mode - User Flow

1. The user clicks edit on an existing chaser cue row in the Cue Sheet.
2. The Chaser Picker is populated with that cue row:
   - chaser selected by `chaser_id`
   - repetitions restored from `data.repetitions`
   - time set to the cue row start time
3. The user clicks `Update` to save the chaser cue row changes.


### Add New Chase - User Flow

TO BE DEFINED (DO NOT IMPLEMENT YET)

- The user click 'New'.
  - The Cue Sheet is set to 'select mode' (checkboxes are shown)
  - The chaser name turns into a text input to allow the user write a name.
  - The 'New' button is hidden.
  - The 'Save' and 'Cancel' buttons are shown.
- The user selects one or more effects from the effects playlist.
  - the first selected effect will be the first of the chase: that is, it will be executed at t+0.
