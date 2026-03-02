# AI Light Show App

## Workflow

### Preparation (outside the UI)
- The user add a song into /backend/songs
- The user executes the /analyzer/analyze_song.py
- When complete: the user start the flow from the UI.

### Song Analysis
Goal: Adjust the song metadata and exact timecode.
Why: This step is crucial to call the right effect with precise time, and to calculate fixture readyness to perform.
How:
- Adjust the song parts labels (example: intro, verse, and so), adjust where the part starts and where ends using wavesurfer; When complete, hits "save"
- Add/remove/edit song point hints labels and exact position (example: claps, hey, drop, and so)

### Show Builder
Goal: Manage the Cue Sheet of the selected song.
Why: To have precise control of the effects/chasers that will be triggered in the timecode.
How:
- The user moves the song cursor to the desired position.
- Using the Effect Picker: select the fixture, the effect, set the optional parameters, preview the effect, and add it to the cue-sheet.
- Using the Chaser Picker: select the chase name, set the optional parameters, preview the chase, and add it to the cue-sheet.

Goal: Create Chasers from selected effects.
Why: To simplify the chase creation based on a song, so it can be re-used in the song or globally.
How:
- Select one or more effect from the Cue Sheet, and hit "save as Chaser".
- The chaser is saved with the timecode offset (the first effect starts at 0, then the following stores the offset)

### DMX Controller
Goal: Control individual fixtures in realtime.
Why: To control effects as an actual DMX Controller console.
How:
- From a fixture panel, set the fixture parameters: the artnet frames are delivered while the controls are changed.

Goal: Preview fixture effects in realtime.
Why: To have a visual reference on how the effects work (on the POIs when referenced)
How:
- From a fixture panel, select the desired effect.
- set the optional parameters and duration, then click on preview.
- the dmx canvas renders the effect on the involved channels, then send the frames to the artnet node (preview the effect).

Goal: Manage POI position for a fixture.
Why: To check and set POIs for each fixture.
- From a fixture panel (moving head), click on a POI to move the head to the recorded position.
- From a fixture panel (moving head), move the pan/tilt to the desired position, then SHIFT+click on a POI to record the position.

### Show Control
Goal: Start and Stop the Light Show
Why: This is the main goal of this application.
How:
- The user clicks Play and the pre-rendered dmx canvas is sent to the artnet node.
- The music is playing in the host.
- The time of the server is syncronized with the play time from the host.
