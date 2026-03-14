# Show Builder - Effect Playlist


## Action Buttons
1. The user seeks the song to the desired position.
2. The user selects one fixture from the dropdown.
3. The UI populates the list of the effects available to the selected fixture.
4. The UI renders the paramenters of the selected effect.
  4.1. if the user select a different fixture that has the current selected effect, the effect does not change (parameters)
  4.2. if the selected fixture does not have the effect, the 'flash' effect is selected or the first available effect.

5. The user change the effect parameters (from step 4).
6. The user click on 'Preview', and the effect is rendered directly to the Artnet/Dmx node (leave other fixtures with their current values)
7. The user click on 'Add', and the effect is stored in the cue at the current position with the selected parameters (from step 5).

## LLM Hints

- [add your definitions here]