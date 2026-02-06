## Analysis Service
A way to execute the analysis service pipeline on a selected song.
A stateless API could be ok, with progress steps to be pushed to the frontend UI.

## Song Selection
when the user clicks on the song name, there's a list of available songs (from backend/songs). 
when select one song to be loaded in the ui (also re-render the backend dmx canvas)

## POI designer
A UI that show a list of POIs (create/update/delete).
At the same time, a list of fixtures: when a fixture is selected, a "fixture panel" is displayed to pan/tilt the actual fixture to the POI position, then save the mapping "fixture pan/tilt values -> poi"

## Chaser designer
A UI that show a list of chasers (create/update/delete).
On select, there is a timeline with fixtures/effects that can be edited.
The chasers should be saved in backend/fixtures/chasers.json

## Song Analyzer UI
A list of songs from backend/songs to choose.
On select, display a list with the metadata and SVG plots to analyze the song IR.
Allow to add LLM hints or instructions to the metadata.
A "button" to request "analyzer" to re-create (overwrite) the metadata files (user LLM hints will be deleted).
A "button" to generate a show plan. Can generate the show for a segment (cues for a segment of the song) or the plan for the whole song (storytelling instructions for each segment).