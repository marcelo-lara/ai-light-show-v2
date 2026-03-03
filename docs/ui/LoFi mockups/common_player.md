# Audio Waveform

## Top

WaveSurfer.js component (https://wavesurfer.xyz/examples)


## Controls (left to right)

### Bar.Beat indicator

Bar is the index of the current downbeat.
Beat is the relative index of the beat to the Bar (last downbeat). Beat should NEVER be greater than 9.
Format: 1.1 (bar.beat) in big numbers

### Position + Playback

- Prev Section: set the song position to the begining of the previous song part (or 0 if there is no previous)
- Prev Beat: set the song position to the previous beat (or 0 if there is no previous beat)
- Stop: Stop playback and go to begining (0)
- Play/Pause: When stopped -> show "Play"; when playing -> show "Pause" (on click, pause and stay at current position)
- Next Beat: set the song position to the next beat (or last beat if there are no more beats)
- Next Section: set the song position to the begining of the next song part (or begining of last part if no more parts)

- Loop Regions: loop the playback to within the boundaries of the selected part 
     - if no part is selected, play until next song part and keep looping the part.
     - if no part is selected and no parts are until the end of the song, don't loop the whole song. stop at the end.

### Show/Hide WaveSurfer Regions

- When checked, show the <label> region on the waveform.

### Zoom Slider

- Zoom level of the WaveSurfer component

