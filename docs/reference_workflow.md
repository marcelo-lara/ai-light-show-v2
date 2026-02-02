# AI Light Show v2

## Basic Usage
### Initial State
* The user selects a song from the backend  "songs" folder.
* The backend creates (or load) the cue sheet with the same name of the song in the "cues" folder.
* The backend creates (or load) the song metadata:
   this metadata has the average BPM, Song Key and 3 digit time of:
   - parts (intro, verse, chorus, and so)
   - hints (drops, claps, tension, and so)
   - drum kicks, snares and hihat
* The backend send the song to the frontend. 
   The frontend uses the [song waveform] placeholder to display the song waveform. 
* The backend sends the fixtures (and its channels) to the frontend to populate the "dmx fixtures" lane
  - the backend is configured with the fixtures.json from the backend/fixtures folder.

### Program State
* The user update the song position (time), the values of the DMX channels are updated with the values of the position of the "cue"
* The user adjust the DMX Fixtures values (from the DMX fixtures placeholder), and select "add to cue"
* "add to cue" sets the DMX values to the current state (values) at the current position (time) of the song.
  this is stored in the "cue" file (in the backend)

### Play State
* When a song is loaded, the frontend and the backend syncronize the timecode.
* when the user selects "play" the song is played in the frontend, and the backend uses the time of each entry on the "cue" to send the values to the ArtNet DMX node. Also the "play" button turns into "stop", to stop playing music and stop rendering the light cue.

## Web UI
The UI contains a main panel in the left, and a side panel on the right.

### Main Panel
The main panel has a header with the component from "https://wavesurfer.xyz/".
Below the main panel header, there are three columns (or "lanes"):
- Song Parts: a list of boxes with [time] [title] [duration] and [type] and [llm hint] fields
   - when a box is selected, the song position moves (change song current time) to the box initial time.
- DMX Cue Sheet: a list of boxes with [time] [(optional)name]
   - when a box is selected, the song position moves (change song current time) to the box initial time.
- DMX Fixtures: a list of available features with [fixture name] and below a list of channels with a slider representing their current value.
   - when a value is changed, the "add to cue" button is enabled to add/edit the cue in the specified time.
   - the backend updates the dmx value in the bytearray and send it to the artnet node.
all three columns are equal in width, and are independantly scrollable.

### Side Panel
The side panel is a "VS Code like" LLM chat, where the user can interact with an LLM to control or modify the cues.
below is a textbox for the user to write a prompt and a send button.
the history is show in a stream-like received from the backend.

## IMPORTANT NOTES
- The DMX Control including cues, song metadata and other related files are stored and managed by the backend. (the frontend does not have direct access to these files)
- The web UI does not has any logic other than display information and control the backend.

