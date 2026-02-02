# DMX Show

The DMX Fixtures are "dumb lights", they only react to the DMX channel values.
In order to produce a "flash" effect, the Fixture class must calculate the channel values at every intermediate step, so when the play button is pressed and the time is right, the dmx channel and values are sent to the artnet node.

A show consists of a "Cue Sheet" and the "dmx canvas".

## Cue Sheets

A "cue sheet" is list of high-level instructions to be interpreted and rendered to the dmx canvas.
There's one cue sheet per song, stored in the backend/cues folder.
when a new song is loaded, the backend reads the cue sheet and invokes the "action" of each fixture to set the DMX values on the "dmx canvas".

### Data
- time: the time in ss.mmm (seconds and millisieconds) when the action should start.
- fixture_id: the fixture that should be performing the action.
- action: the action or effect the fixture must perform.
- duration: the time for the action to last.
- data: additional parameters that could be required for the action.

example:
"1.123 parcan_l flash 1.000"
means: "at 1.123 seconds of the timeline, render the 'flash' effect on parcan_l (set RGB to 255) and then gradually decrease to 0 in 1.000 seconds since flash start"


## DMX Canvas

The DMX canvas is an array of bytearrays frames with the entire values of the ArtNet universe and the exact time when it should be delivered.
This DMX canvas should be delivered at 60FPS (about 16.67ms per frame) to the artnet node.
the time is the strictly tied to the song time, so when the song is at 60s, the DMX Canvas should deliver the 60.000 artnet frame to the artnet node.
This DMX Canvas should be available to the Fixture Classes to render the effects.
The canvas is reset (all values to 0) on the song change, and will be updated by the cue sheet.
This canvas will not be persisted, just calculated from the cue sheet.

## Fixture "action render" function

each fixture has a list of "actions" function thats writes the values to a cue sheet, so when the dmx dispatcher is requested to play the cue sheet, the dmx values are sent to produce the desired effect on the light fixture.

example: "flash" by "1" (second) from "FFFFFF" at "0.5" in a parcan means that the parcan must be armed before 0.5 seconds (if not already armed) and set all RBB channels to 255 at 0.500 seconds of the cue sheet and gradually decrease to end with 0 at 1.5 seconds of the cue sheet

example: "move_to" "1234x 3456y" by "1" (second) in a moving head, means that the MovingHead class must calculate the current pan and tilt position (16bits) to set the new values of pan and tilt, calculating the intermediate steps to arrive to the final position in 1 second.

by its nature, each fixture type can perform different actions. 
Example: a parcan can render RGB colors, while a moving head has a color wheel (discrete number of colors).
Example: a moving_head can move in two dimensions (pan/tilt), while a parcan has a fixed position (no pan, no tilt).


